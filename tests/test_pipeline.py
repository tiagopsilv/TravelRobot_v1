import asyncio
import csv
from datetime import date, datetime
from decimal import Decimal

from travelrobot.models import GuestReviews, HotelOffer, Promotion
from travelrobot.pipeline import Sources, deduplicate, run_pipeline

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
    async def collect(self):
        return [Promotion(NOW, "Smiles", "Tipo", "Título; com separador", "Texto", "Até 10", "x")]


class FakeDistances:
    def __init__(self, error=None):
        self.addresses, self.error = [], error

    async def distance_km(self, address, reference_point):
        self.addresses.append(address)
        if self.error:
            raise self.error
        return Decimal("3.200")


def sources(offers, distances=None):
    return Sources(offers, FakePromotions(), distances or FakeDistances())


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
    path = tmp_path / "FrequentFlyersList_Smiles_20270101.csv"
    with path.open(encoding="utf-8-sig", newline="") as file:
        assert next(csv.DictReader(file, delimiter=";"))["titulo"] == "Título; com separador"


def test_html_is_saved_per_city(window, tmp_path):
    run(window, tmp_path, sources([FakeOffers("Decolar", [offer()])]))
    html = (tmp_path / "Htmls" / "HtmlHotel_LosAngeles_20270101.html").read_text(encoding="utf-8")
    assert "<p>Hotel A</p>" in html
