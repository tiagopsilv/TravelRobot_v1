"""Testes com HTML sintético: validam a lógica de parsing, não se os sites reais ainda usam esses seletores."""
import json
from collections import Counter
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from travelrobot.browser import SourceBlocked, raise_if_blocked
from travelrobot.sources import decolar, google_hotels, google_maps, pontos_pra_voar, smiles

NOW = datetime(2027, 1, 1, 12)


def test_decolar_url_has_valid_query_string(window):
    assert decolar.build_url(window, 2) == (
        "https://www.decolar.com/accommodations/results/CIT_1/2027-03-23/2027-03-25/?page=2"
    )


def test_decolar_skips_broken_card_and_keeps_the_others(window, selectors):
    html = """
    <div class="results-cluster-container">
      <span class="accommodation-name -eva-3-ellipsis"> Hotel A </span>
      <span class="main-value">1.234,50</span>
      <p class="tooltip-text -eva-3-mb-xsm">Nota 8.5</p>
      <p class="eva-3-p -eva-3-tc-gray-0 first-message">2 noites, 3 pessoas</p>
    </div>
    <div class="results-cluster-container"><span class="main-value">10</span></div>
    <div class="results-cluster-container">
      <span class="accommodation-name -eva-3-ellipsis">Hotel C</span>
      <span class="main-value">500</span>
    </div>"""
    offers = decolar.parse_results(html, window, selectors.decolar, NOW)
    assert [offer.hotel_name for offer in offers] == ["Hotel A", "Hotel C"]
    assert offers[0].price == Decimal("1234.50")
    assert offers[0].rating == Decimal("8.5")
    assert offers[0].people == 3
    assert offers[0].nights == 2
    assert offers[0].address is None


def test_google_hotel_list(selectors):
    html = """<div class="pjDrrc">
      <a class="aS3xV lRagtb xl0RMe" href="/travel/hotels/entity/1"></a>
      <h2 class="BgYkof ogfYpf ykx2he">Hotel A</h2>
      <span class="KFi5wf lA0BZ">4,5</span>
    </div>
    <div class="pjDrrc"><h2 class="BgYkof ogfYpf ykx2he">Sem link</h2></div>"""
    hotels = google_hotels.parse_hotel_list(html, selectors.google_hotels)
    assert hotels == [
        google_hotels.HotelCandidate(
            "Hotel A", "https://www.google.com.br/travel/hotels/entity/1", Decimal("4.5")
        )
    ]


def test_google_offers(window, selectors):
    hotel = google_hotels.HotelCandidate("Hotel A", "https://x", Decimal("4.5"))
    html = """<div class="K4nuhf"><span class="CFH2De">Rua 1</span></div>
    <div class="ADs2Tc">
      <span class="NiGhzc"> Booking.com </span><span class="nDkDDb">R$ 900</span>
      <a class="hUGVEe cTvP0c" href="/aclk?adurl=http://site.com/h"></a>
    </div>
    <div class="ADs2Tc"><span class="NiGhzc">Sem preço</span></div>"""
    offers = google_hotels.parse_offers(html, hotel, window, selectors.google_hotels, NOW)
    assert len(offers) == 1
    assert offers[0].source == "Booking.com"
    assert offers[0].price == Decimal("900")
    assert offers[0].address == "Rua 1"
    assert offers[0].link == "http://site.com/h"
    assert offers[0].rating == Decimal("4.5")


def test_google_price_currency_is_kept(window, selectors):
    hotel = google_hotels.HotelCandidate("Hotel A", "https://x", None)
    html = """<div class="ADs2Tc"><span class="NiGhzc">Expedia</span>
      <span class="nDkDDb">US$ 129</span></div>"""
    offer = google_hotels.parse_offers(html, hotel, window, selectors.google_hotels, NOW)[0]
    assert (offer.price, offer.currency) == (Decimal("129"), "USD")


def _topic(label, css=""):
    return f'<button class="WAWozd {css}"><span class="m1GHmf">{label}</span></button>'


# Mesma estrutura da aba de avaliações real em nov/2026: a lista lateral também tem aria-labels de nota.
REVIEWS_PAGE = f"""
<div aria-label="4 de 5 estrelas em 824 avaliações">Outro hotel da lista</div>
<span id="overview"><div aria-label="9,9 de 5 estrelas em 9 avaliações"></div></span>
<span id="reviews">
  <h2>Resumo de avaliações do Google</h2>
  <div class="FBsWCd">3,6</div>
  <span aria-label="3,6 de 5 estrelas em 1.623 avaliações"></span>
  {_topic("Pesquisar avaliações")}
  {_topic("Banheiro (116)")}
  {_topic("Limpeza (111)", "HPIhNd")}
  {_topic("Local (76)", "HPIhNd")}
  {_topic("Quarto (45)", "lErJIb")}
  {_topic("Mais 10", "HPIhNd")}
  <div class="TL1fMd F0n91b">
    <span class="xtsqwb">Tripadvisor</span>
    <div class="s97yQ"><span>3,4/5</span> <span>· 225 avaliações</span></div>
  </div>
  <div class="TL1fMd"></div>
</span>"""


def test_google_reviews_read_only_the_open_hotel(selectors):
    reviews = google_hotels.parse_reviews(REVIEWS_PAGE, selectors.google_hotels)
    assert reviews.rating == Decimal("3.6")
    assert reviews.review_count == 1623
    assert reviews.positive_topics == ["Limpeza (111)", "Local (76)"]
    assert reviews.negative_topics == ["Quarto (45)"]
    assert reviews.other_sites == ["Tripadvisor: 3,4/5 · 225 avaliações"]


@pytest.mark.parametrize("html", ["<html></html>", '<span id="reviews"><p>Sem resumo</p></span>'])
def test_google_reviews_absent(selectors, html):
    assert google_hotels.parse_reviews(html, selectors.google_hotels) is None


@pytest.mark.parametrize(
    ("displayed", "expected", "matches"),
    [
        ("qui., 25 de mar.", date(2027, 3, 25), True),
        ("qua., 24 de mar.", date(2027, 3, 25), False),
        ("qui., 25 de mar.", date(2027, 3, 5), False),
        ("ter., 5 de jan.", date(2027, 3, 5), False),
    ],
)
def test_google_date_check_catches_wrong_stay(displayed, expected, matches):
    assert google_hotels.date_matches(displayed, expected) is matches


def test_google_maps_distance_in_meters(selectors):
    html = '<div class="ivN21e tUEI8e fontBodyMedium"><div>800 m</div></div>'
    assert google_maps.parse_distance(html, selectors.google_maps) == Decimal("0.800")


def test_google_maps_url_encodes_addresses():
    url = google_maps.build_url("Rua A/B, 1", "Times Square")
    assert url.startswith("https://www.google.com/maps/dir/Rua%20A%2FB%2C%201/Times%20Square/")


FIXTURES = Path(__file__).parent / "fixtures"
PROMO_NOW = datetime(2026, 11, 10, 12)  # data em que as fixtures foram salvas


def test_smiles_keeps_only_running_promotions(selectors):
    # JSON real de nov/2026, reduzido: o "Ativa" de 2024 vencido e o encerrado ficam de fora.
    payload = (FIXTURES / "smiles_promotions.json").read_text(encoding="utf-8")
    promotions = smiles.parse_promotions(payload, selectors.smiles, PROMO_NOW)
    assert [p.title for p in promotions] == [
        "Sua viagem ganha um novo destaque!",
        "Planeje sua viagem",
        "Seu Clube Smiles pode mais!",
    ]
    first = promotions[0]
    assert (first.source, first.program, first.kind) == ("Smiles", "Smiles", "Viagem")
    assert first.description == "Smiles & Money"
    assert first.end == date(2026, 12, 31)
    assert first.link == "https://www.smiles.com.br/mfe/trens"
    assert promotions[1].end == PROMO_NOW.date()  # termina hoje: ainda vale
    assert promotions[2].description == "Até 15% OFF! · Exclusiva Clube Smiles"


def _smiles_item(**fields):
    return {"contentFields": [{"name": k, "contentFieldValue": {"data": v}} for k, v in fields.items()]}


def test_smiles_relative_link_and_missing_dates(selectors):
    payload = json.dumps(
        {"items": [_smiles_item(PromocaoAtivaOuEncerrada="Ativa", TituloCard="T", LinkDaPromocao="/x")]}
    )
    promotion = smiles.parse_promotions(payload, selectors.smiles, PROMO_NOW)[0]
    assert promotion.link == "https://www.smiles.com.br/x"
    assert (promotion.start, promotion.end, promotion.kind) == (None, None, "")


@pytest.mark.parametrize("payload", ['{"items": []}', json.dumps({"items": [_smiles_item(title="x")]})])
def test_smiles_rejects_json_that_is_not_the_promotions_list(selectors, payload):
    # Outra coleção capturada por engano não pode virar "zero promoções" sem aviso.
    with pytest.raises(ValueError, match="formato esperado"):
        smiles.parse_promotions(payload, selectors.smiles, PROMO_NOW)


RADAR = (FIXTURES / "radar_ppv.html").read_text(encoding="utf-8")


def test_radar_reads_every_table_and_drops_expired_rows():
    # Post real de 9/11/2026, com três linhas por tabela.
    promotions = pontos_pra_voar.parse_post(RADAR, date(2026, 11, 9), PROMO_NOW)
    kinds = Counter(p.kind for p in promotions)
    assert set(kinds) == {
        "Acúmulo de pontos", "Transferência de pontos", "Compra de pontos com desconto",
        "Compra de pontos com bônus", "Adesão de clubes", "Upgrade de clubes",
    }  # fmt: skip
    assert all(p.end is None or p.end >= PROMO_NOW.date() for p in promotions)
    assert "Clube Bancorbrás" not in {p.partner for p in promotions}  # venceu em 9 de novembro


def test_radar_row_fields():
    promotions = pontos_pra_voar.parse_post(RADAR, date(2026, 11, 9), PROMO_NOW)
    transfer = next(p for p in promotions if p.kind == "Transferência de pontos")
    assert (transfer.program, transfer.partner) == ("Azul Fidelidade", "C6 Bank")
    assert (transfer.benefit, transfer.value) == ("Bonificação até 120%", Decimal("120"))
    assert transfer.end == date(2026, 11, 10)
    assert transfer.link.startswith("https://pontospravoar.com/")
    discount = next(p for p in promotions if p.kind == "Compra de pontos com desconto")
    assert (discount.program, discount.partner) == ("Finnair Plus Avios", None)
    club = next(p for p in promotions if p.kind == "Adesão de clubes" and p.end == date(2026, 11, 30))
    assert (club.program, club.benefit, club.value) == (
        "Smiles", "Bônus ou desconto até 10.000", Decimal("10000")
    )


@pytest.mark.parametrize(
    ("validity", "published", "expected"),
    [
        ("30 de novembro (21h)", date(2026, 11, 9), date(2026, 11, 30)),
        ("15 de janeiro", date(2026, 12, 20), date(2027, 1, 15)),  # virada de ano
        ("5 de novembro", date(2026, 11, 9), date(2026, 11, 5)),  # já vencida, mesmo ano
        ("31 de dezembro", date(2027, 1, 1), date(2026, 12, 31)),  # vencida na véspera, ano anterior
        ("29 de fevereiro", date(2027, 12, 20), date(2028, 2, 29)),  # próximo ano bissexto
        ("29 de fevereiro", date(2027, 2, 10), date(2024, 2, 29)),  # 2028 passa de 300 dias: antiga
        ("1 de outubro", date(2026, 11, 9), date(2026, 10, 1)),  # linha antiga, não outubro de 2027
        ("5 de setembro", date(2026, 11, 9), date(2027, 9, 5)),  # exatamente 300 dias à frente
        ("6 de setembro", date(2026, 11, 9), date(2026, 9, 6)),  # 301 dias: tratada como antiga
        ("9 de outubro", date(2026, 11, 9), date(2026, 10, 9)),  # 31 dias antes, mesmo ano
        ("Indeterminada", date(2026, 11, 9), None),
        ("31 de fevereiro", date(2026, 11, 9), None),
    ],
)
def test_radar_validity_without_year(validity, published, expected):
    assert pontos_pra_voar._end_date(validity, published) == expected


def test_radar_drops_old_row_instead_of_moving_it_to_next_year():
    html = """<h2>Promoções de transferência de pontos</h2><table>
      <tr><th>Programa</th><th>Parceiro</th><th>Bonificação (Até)</th><th>Validade</th></tr>
      <tr><td>Smiles</td><td>Livelo</td><td>80</td><td>1 de outubro</td></tr>
      <tr><td>Azul</td><td>Livelo</td><td>90</td><td>30 de novembro</td></tr></table>"""
    promotions = pontos_pra_voar.parse_post(html, date(2026, 11, 9), PROMO_NOW)
    assert [(p.program, p.end) for p in promotions] == [("Azul", date(2026, 11, 30))]


def test_radar_unknown_validity_is_kept_as_text():
    html = """<h2>Promoções de transferência de pontos</h2><table>
      <tr><th>Programa</th><th>Parceiro</th><th>Bonificação (Até)</th><th>Validade</th></tr>
      <tr><td>Smiles</td><td>Livelo</td><td>8¹</td><td>Enquanto durar</td></tr></table>"""
    promotion = pontos_pra_voar.parse_post(html, date(2026, 11, 9), PROMO_NOW)[0]
    assert (promotion.end, promotion.description) == (None, "Enquanto durar")
    assert (promotion.benefit, promotion.value, promotion.link) == ("Bonificação até 8", Decimal("8"), "")


def test_radar_picks_latest_real_radar_post(selectors):
    payload = json.dumps([
        {"date": "2026-11-10T09:00:00", "title": {"rendered": "Outro post que cita o Radar PPV"}},
        {"date": "2026-11-08T20:00:00", "title": {"rendered": "Radar PPV! Resumo do dia 8"}},
        {"date": "2026-11-09T20:00:00", "title": {"rendered": "Radar PPV! Resumo &#8211; dia 9"}},
    ])  # fmt: skip
    post = pontos_pra_voar.latest_post(payload, selectors.pontos_pra_voar)
    assert post["date"] == "2026-11-09T20:00:00"
    assert pontos_pra_voar.latest_post("[]", selectors.pontos_pra_voar) is None


@pytest.mark.parametrize("status", [202, 403, 429])
def test_blocked_statuses_are_reported(status):
    with pytest.raises(SourceBlocked, match=str(status)):
        raise_if_blocked(SimpleNamespace(status=status), "Site")


def test_normal_status_is_not_blocked():
    raise_if_blocked(SimpleNamespace(status=200), "Site")
    raise_if_blocked(None, "Site")
