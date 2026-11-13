import asyncio
import csv
import json
from datetime import date, datetime
from decimal import Decimal

from travelrobot.models import GuestReviews, HotelOffer, Promotion
from travelrobot.pipeline import Sources, deduplicate, run_pipeline
from travelrobot.sources import esfera, livelo, pontos_pra_voar, smiles
from travelrobot.storage import FEED_COLUMNS, PROMOTION_COLUMNS, SOURCE_COLUMNS, save_promotions

RUN_DATE = date(2027, 1, 1)
NOW = datetime(2027, 1, 1, 12)


def offer(hotel="Hotel A", source="Decolar", address=None, price="100", reviews=None):
    return HotelOffer(
        executed_at=NOW, source=source, city_name="LosAngeles", hotel_name=hotel,
        check_in=date(2027, 3, 23), check_out=date(2027, 3, 25), price=Decimal(price),
        address=address, html=f"<p>{hotel}</p>", reviews=reviews,
    )  # fmt: skip


class FakeOffers:
    def __init__(self, name, result):
        self.name, self.result = name, result

    async def collect(self, window):
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class FakePromotions:
    def __init__(self, name="Smiles", error=None):
        self.name, self.error = name, error

    async def collect(self):
        if self.error:
            raise self.error
        return [
            Promotion(
                NOW, self.name, "Smiles", "Viagem", title="Título; com separador",
                value=Decimal("120.5"), end=date(2027, 1, 31),
            )
        ]  # fmt: skip


class FakeDistances:
    def __init__(self, error=None):
        self.addresses, self.error = [], error

    async def distance_km(self, address, reference_point):
        self.addresses.append(address)
        if self.error:
            raise self.error
        return Decimal("3.200")


def sources(offers, distances=None, promotions=None):
    return Sources(offers, promotions or [FakePromotions()], distances or FakeDistances())


def run(window, tmp_path, built):
    return asyncio.run(run_pipeline([window], built, tmp_path, RUN_DATE))


def read_rows(tmp_path):
    path = tmp_path / "HotelsList_LosAngeles_20270101.csv"
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file, delimiter=";"))


def test_reviews_are_written_to_csv(window, tmp_path):
    reviews = GuestReviews(
        rating=Decimal("3.6"),
        review_count=623,
        positive_topics=["Limpeza (111)", "Local (76)"],
        negative_topics=["Quarto (45)"],
        other_sites=["Tripadvisor: 3,4/5 · 225 avaliações"],
    )
    report = run(
        window,
        tmp_path,
        sources([FakeOffers("Google", [offer(source="Expedia", address="Rua 1", reviews=reviews)])]),
    )
    row = read_rows(tmp_path)[0]
    assert row["avaliacao_nota"] == "3,6"
    assert row["avaliacao_quantidade"] == "623"
    assert row["temas_positivos"] == "Limpeza (111) | Local (76)"
    assert row["temas_negativos"] == "Quarto (45)"
    assert row["notas_outros_sites"] == "Tripadvisor: 3,4/5 · 225 avaliações"
    assert report.hotels_with_reviews == 1


def test_offer_without_details_gets_them_from_same_hotel_in_other_source(window, tmp_path):
    reviews = GuestReviews(rating=Decimal("4.0"))
    distances = FakeDistances()
    collected = [offer(), offer(hotel=" hotel a", source="Expedia", address="Rua 1", reviews=reviews)]
    report = run(window, tmp_path, sources([FakeOffers("X", collected)], distances))

    assert distances.addresses == ["Rua 1"]
    rows = read_rows(tmp_path)
    assert [row["endereco"] for row in rows] == ["Rua 1", "Rua 1"]
    assert [row["avaliacao_nota"] for row in rows] == ["4,0", "4,0"]
    assert [row["distancia_km"] for row in rows] == ["3,200", "3,200"]
    assert report.hotels == report.hotels_with_reviews == report.hotels_with_distance == 1


def test_failing_source_does_not_lose_the_other(window, tmp_path):
    report = run(
        window,
        tmp_path,
        sources([FakeOffers("Google", RuntimeError("bloqueado")), FakeOffers("Decolar", [offer()])]),
    )
    assert report.offers == 1
    assert len(report.failures) == 1
    assert "bloqueado" in report.failures[0]


def test_failed_distance_keeps_collected_offers(window, tmp_path):
    distances = FakeDistances(error=RuntimeError("captcha"))
    collected = [offer(address="Rua 1")]
    report = run(window, tmp_path, sources([FakeOffers("Decolar", collected)], distances))
    assert len(read_rows(tmp_path)) == 1
    assert any("captcha" in failure for failure in report.failures)


def test_no_offers_writes_no_hotel_file(window, tmp_path):
    report = run(window, tmp_path, sources([FakeOffers("Decolar", [])]))
    assert report.offers == 0
    assert not (tmp_path / "HotelsList_LosAngeles_20270101.csv").exists()


def test_distance_is_fetched_once_per_hotel(window, tmp_path):
    distances = FakeDistances()
    collected = [
        offer(source="A", address="Rua 1"),
        offer(source="B", address="Rua 1"),
        offer(hotel="  hotel a ", source="C", address="Rua 1"),
    ]
    run(window, tmp_path, sources([FakeOffers("X", collected)], distances))
    assert distances.addresses == ["Rua 1"]


def test_deduplicate_keeps_different_sites():
    result = deduplicate([offer(source="A"), offer(source="A", price="200"), offer(source="B")])
    assert [(o.source, o.price) for o in result] == [("A", Decimal("100")), ("B", Decimal("100"))]


def test_csv_escapes_separator_in_values(window, tmp_path):
    run(window, tmp_path, sources([FakeOffers("Decolar", [offer(hotel="Hotel; Plaza")])]))
    assert read_rows(tmp_path)[0]["hotel"] == "Hotel; Plaza"
    path = tmp_path / "FrequentFlyersList_20270101.csv"
    with path.open(encoding="utf-8-sig", newline="") as file:
        row = next(csv.DictReader(file, delimiter=";"))
    assert row["titulo"] == "Título; com separador"
    assert (row["valor"], row["fim"], row["parceiro"]) == ("120,5", "2027-01-31", "")


def test_failing_promotion_source_does_not_stop_the_others(window, tmp_path):
    promotions = [FakePromotions("Smiles", RuntimeError("fora do ar")), FakePromotions("Radar")]
    report = run(window, tmp_path, sources([], promotions=promotions))
    assert report.promotions_by_source == {"Radar": 1}
    assert any("Promoções Smiles" in failure for failure in report.failures)
    assert (tmp_path / "FrequentFlyersList_20270101.csv").exists()


def _csv(path):
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, delimiter=";")
        return reader.fieldnames, list(reader)


def test_each_promotion_source_also_gets_its_own_csv(window, tmp_path):
    names = ["Smiles", "Pontos pra Voar (Radar PPV)", "Melhores Cartões"]
    promotions = [FakePromotions(name) for name in names]
    run(window, tmp_path, sources([], promotions=promotions))
    columns, rows = _csv(tmp_path / "FrequentFlyersList_20270101.csv")
    assert (columns, len(rows)) == (PROMOTION_COLUMNS, 3)

    folder = tmp_path / "Promocoes"
    assert sorted(path.name for path in folder.iterdir()) == [
        "FrequentFlyersList_MelhoresCartoes_20270101.csv",
        "FrequentFlyersList_PontosPraVoarRadarPPV_20270101.csv",
        "FrequentFlyersList_Smiles_20270101.csv",
    ]
    columns, rows = _csv(folder / "FrequentFlyersList_Smiles_20270101.csv")
    assert columns == SOURCE_COLUMNS["Smiles"]
    assert "fonte" not in columns and "prazo_credito_dias" not in columns
    assert (len(rows), rows[0]["titulo"], rows[0]["valor"]) == (1, "Título; com separador", "120,5")
    columns, _ = _csv(folder / "FrequentFlyersList_MelhoresCartoes_20270101.csv")
    assert columns == FEED_COLUMNS  # blogs: o nome vem da configuração


def test_source_columns_match_sources_and_consolidated_csv():
    assert set(SOURCE_COLUMNS) == {smiles.SOURCE, livelo.SOURCE, esfera.SOURCE, pontos_pra_voar.SOURCE}
    for columns in [*SOURCE_COLUMNS.values(), FEED_COLUMNS]:
        assert set(columns) <= set(PROMOTION_COLUMNS) and len(set(columns)) == len(columns)


def test_html_is_saved_per_city(window, tmp_path):
    run(window, tmp_path, sources([FakeOffers("Decolar", [offer()])]))
    html = (tmp_path / "Htmls" / "HtmlHotel_LosAngeles_20270101.html").read_text(encoding="utf-8")
    assert "<p>Hotel A</p>" in html


def test_sources_with_names_that_normalize_alike_get_separate_files(tmp_path):
    names = ["Blog A", "Blog Á", "blog a", "Smiles"]
    promotions = [Promotion(NOW, name, "Smiles", "Notícia", title=name) for name in names]
    paths = save_promotions(promotions, tmp_path, date(2027, 1, 1))
    assert len(paths) == len(set(path.name.casefold() for path in paths)) == 5  # consolidado + 4 fontes
    assert (tmp_path / "Promocoes" / "FrequentFlyersList_Smiles_20270101.csv") in paths
    titles = sorted(_csv(path)[1][0]["titulo"] for path in paths[1:])
    assert titles == sorted(names)  # nenhum arquivo sobrescreveu outro
    assert len(_csv(paths[0])[1]) == 4


def test_source_csv_keeps_coupon_extracted_by_the_parser(selectors, tmp_path):
    fields = {"PromocaoAtivaOuEncerrada": "Ativa", "TituloCard": "Use o cupom SMILES10 na compra de milhas"}
    payload = json.dumps({"items": [{"contentFields": [
        {"name": name, "contentFieldValue": {"data": value}} for name, value in fields.items()
    ]}]})  # fmt: skip
    promotions = smiles.parse_promotions(payload, selectors.smiles, NOW)
    save_promotions(promotions, tmp_path, date(2027, 1, 1))
    _, rows = _csv(tmp_path / "Promocoes" / "FrequentFlyersList_Smiles_20270101.csv")
    assert rows[0]["cupom"] == "SMILES10"
