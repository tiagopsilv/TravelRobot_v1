"""Testes com HTML sintético: validam a lógica de parsing, não se os sites reais ainda usam esses seletores."""
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from travelrobot.browser import SourceBlocked, raise_if_blocked
from travelrobot.sources import decolar, google_hotels, google_maps, smiles

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


def test_smiles_promotions(selectors):
    # Mesma estrutura da página real em nov/2026.
    html = """<a class="x" data-test-idpromotion="584" href="/portal/campanhas/1">
      <div data-testid="card-container">
        <div data-testid="promotion-image"></div>
        <div>
          <div>Comprar Milhas</div>
          <div>Planeje sua viagem</div>
          <div><p>Ofertas para viajar.</p></div>
          <div><div data-testid="bullet"><p>Planeje agora!</p></div></div>
          <div>Válido até:  10/11/2026</div>
        </div>
      </div>
    </a>
    <a data-test-idpromotion="585" href="/x"><div data-testid="card-container"></div></a>"""
    promotions = smiles.parse_promotions(html, selectors.smiles, NOW)
    assert len(promotions) == 1
    assert promotions[0].type == "Comprar Milhas"
    assert promotions[0].title == "Planeje sua viagem"
    assert promotions[0].text == "Ofertas para viajar."
    assert promotions[0].validity == "10/11/2026"
    assert promotions[0].link == "https://www.smiles.com.br/portal/campanhas/1"


@pytest.mark.parametrize(
    ("image", "expected"),
    [("BUSCAR_VOOS.png/f7b0?t=1", "Buscar Voos"), ("Comprar+Milhas.png", "Comprar Milhas")],
)
def test_smiles_type_comes_from_image_name(selectors, image, expected):
    html = f"""<a data-test-idpromotion="1" href="/x"><div data-testid="card-container">
      <div></div>
      <div>
        <div><img src="https://www.smiles.com.br/documents/1/2/{image}"></div>
        <div>Título</div>
      </div>
    </div></a>"""
    assert smiles.parse_promotions(html, selectors.smiles, NOW)[0].type == expected


@pytest.mark.parametrize("status", [202, 403, 429])
def test_blocked_statuses_are_reported(status):
    with pytest.raises(SourceBlocked, match=str(status)):
        raise_if_blocked(SimpleNamespace(status=status), "Site")


def test_normal_status_is_not_blocked():
    raise_if_blocked(SimpleNamespace(status=200), "Site")
    raise_if_blocked(None, "Site")
