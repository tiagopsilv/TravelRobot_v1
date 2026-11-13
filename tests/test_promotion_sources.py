import asyncio
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import json

import pytest

from travelrobot.browser import SourceBlocked
from travelrobot.config import EsferaSelectors, FeedSelectors, LiveloSelectors
from travelrobot.pipeline import Sources, run_pipeline
from travelrobot.sources import esfera, feeds, livelo
from travelrobot.models import Promotion
from travelrobot.sources._promo_text import (
    benefit_value,
    club_only,
    club_value,
    extract_benefit,
    infer_kind,
    value_unit,
)
from travelrobot.storage import PROMOTION_COLUMNS, _promotion_row

FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 11, 10, 12)


def fixture(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


# Livelo


def test_livelo_partners_keeps_running_promotions_only():
    # Fixture real: 3 parceiros em promoção, 1 sem promoção (BAU) e 1 sem paridade.
    promotions = livelo.parse_partners(fixture("livelo_partners.json"), NOW)
    assert [p.partner for p in promotions] == ["ADCOS", "Aramis", "Asics"]
    asics = promotions[2]
    assert asics.benefit == "3 pontos por R$ 1 (5 no Clube Livelo); normal: 1"
    assert (asics.value, asics.start, asics.end) == (Decimal("3"), date(2026, 11, 2), date(2026, 11, 30))
    assert asics.link == "https://livelo.com.br/juntar-pontos/parceiros/asics/ACS"


def test_livelo_partners_drops_expired_promotion():
    later = datetime(2026, 11, 11, 9)
    assert [p.partner for p in livelo.parse_partners(fixture("livelo_partners.json"), later)] == ["Asics"]


def test_livelo_partners_rejects_other_page():
    with pytest.raises(ValueError, match="formato esperado"):
        livelo.parse_partners(fixture("livelo_offers.json"), NOW)


def test_livelo_offers_reads_active_cards_once():
    promotions = livelo.parse_offers(fixture("livelo_offers.json"), NOW)
    assert len(promotions) == len({p.title for p in promotions}) == 5
    smiles = next(p for p in promotions if "Smiles" in p.title)
    assert (smiles.kind, smiles.benefit, smiles.value) == ("Transferência de pontos", "até 70% de bônus", Decimal("70"))
    assert smiles.link == "https://www.livelo.com.br/livelo-para-parceiros/smiles/SMLTransfer"


def test_livelo_offer_with_past_countdown_is_dropped():
    countdown = {"startDate": "2026-11-01T03:00:00Z", "endDate": "2026-11-09T02:59:00Z"}
    assert livelo.parse_offers(_card(countdown=countdown), NOW) == []


# Esfera


def test_esfera_keeps_short_campaigns_and_drops_permanent():
    promotions, last = esfera.parse_campaigns(fixture("esfera_campaigns.json"), NOW)
    assert last is False
    assert [p.partner for p in promotions] == ["Nike", "Beleza na Web", "Renner", "Hoteis.com"]
    hotels = promotions[3]
    assert hotels.benefit == (
        "3 pontos a cada 1 real para clientes em geral · 4 pontos a cada 1 real para clientes clube"
    )
    assert (hotels.value, hotels.start, hotels.end) == (Decimal("3"), date(2026, 11, 10), date(2026, 11, 13))


def test_esfera_drops_long_internal_campaigns():
    campaigns = [
        {"partnerName": "Santander Cartoes", "campaignName": "Correção Santander Rewards",
         "startDate": "2026-07-21T00:00:00", "deadline": "2030-12-31T23:59:00", "partnerParity": 1},
        {"partnerName": "Polishop", "campaignName": "Polishop - 10x1",
         "startDate": "2026-11-09T00:00:00", "deadline": "2026-11-11T23:59:00", "partnerParity": 10},
    ]  # fmt: skip
    promotions, _ = esfera.parse_campaigns(json.dumps({"content": campaigns, "last": True}), NOW)
    assert [p.partner for p in promotions] == ["Polishop"]


def test_esfera_drops_expired_and_rejects_unexpected_payload():
    later = datetime(2026, 11, 12, 9)
    promotions, _ = esfera.parse_campaigns(fixture("esfera_campaigns.json"), later)
    assert [p.partner for p in promotions] == ["Renner", "Hoteis.com"]
    with pytest.raises(ValueError, match="formato esperado"):
        esfera.parse_campaigns('{"items": []}', NOW)


# Feeds RSS

RSS = """<rss><channel>
<item><title>Azul Fidelidade oferece até 120% de bônus nas transferências do Itaú</title>
  <link>https://blog/1</link><pubDate>Mon, 09 Nov 2026 20:00:00 -0300</pubDate>
  <category>Promoções</category><category>Transferência de pontos</category></item>
<item><title>Só hoje! Livelo oferece 104 mil pontos na assinatura do Clube</title>
  <link>https://blog/2</link><pubDate>Mon, 09 Nov 2026 09:00:00 -0300</pubDate>
  <category>Promoções</category></item>
<item><title>Último dia! Ganhe até 11 pontos Livelo por real em lojas parceiras</title>
  <link>https://blog/3</link><pubDate>Tue, 10 Nov 2026 08:00:00 -0300</pubDate>
  <category>Promoções</category></item>
<item><title>Mercado Livre libera cupons de até R$ 200</title>
  <link>https://blog/4</link><pubDate>Tue, 10 Nov 2026 08:00:00 -0300</pubDate>
  <category>Promoções</category></item>
<item><title>Smiles oferece 70% de bônus</title>
  <link>https://blog/5</link><pubDate>Tue, 03 Nov 2026 08:00:00 -0300</pubDate>
  <category>Promoções</category></item>
<item><title>LATAM Pass: 25% de bônus</title>
  <link>https://blog/6</link><pubDate>Tue, 10 Nov 2026 08:00:00 -0300</pubDate>
  <category>Publicidade</category></item>
</channel></rss>"""


def feed(categories=("Promoções",)):
    return FeedSelectors(name="Blog", urls=["https://blog/feed"], categories=list(categories))


def test_feed_keeps_recent_items_about_programs():
    # Fora: notícia velha (3/11), sem programa (Mercado Livre), categoria errada e "Só hoje!" de ontem.
    promotions = feeds.parse_feed(RSS, feed(), NOW)
    assert [p.link for p in promotions] == ["https://blog/1", "https://blog/3"]
    azul, livelo_day = promotions
    assert (azul.source, azul.program, azul.kind) == ("Blog", "Azul Fidelidade, Itaú", "Transferência de pontos")
    assert (azul.benefit, azul.value, azul.published, azul.start, azul.end) == (
        "até 120% de bônus", Decimal("120"), date(2026, 11, 9), None, None
    )
    assert (livelo_day.kind, livelo_day.end) == ("Acúmulo de pontos", date(2026, 11, 10))


def test_feed_without_category_filter_accepts_all_categories():
    links = [p.link for p in feeds.parse_feed(RSS, feed(categories=()), NOW)]
    assert "https://blog/6" in links


@pytest.mark.parametrize(
    ("text", "kind", "benefit", "value"),
    [
        ("Transfira pontos Nubank para a Smiles com até 80% de bônus", "Transferência de pontos",
         "até 80% de bônus", Decimal("80")),
        ("Ganhe até 15 pontos Azul Fidelidade por real gasto", "Acúmulo de pontos",
         "até 15 pontos Azul Fidelidade por real", Decimal("15")),
        ("Smiles oferece cupom de 79% de desconto na compra de milhas", "Compra de pontos",
         "79% de desconto", Decimal("79")),
        ("Livelo oferece 23.000 pontos no Clube Essencial", "Clubes", "23.000 pontos", Decimal("23000")),
        ("Livelo oferece 104 mil pontos na assinatura", "Clubes", "104 mil pontos", Decimal("104000")),
        ("Melhores resgates com a Livelo", "Notícia", "", None),
    ],
)  # fmt: skip
def test_kind_and_benefit_from_text(text, kind, benefit, value):
    assert (infer_kind(text), extract_benefit(text), benefit_value(extract_benefit(text))) == (kind, benefit, value)


# Achados da revisão do Codex


def _card(**overrides):
    card = {
        "ContentTypeUid": "cb_previsibility", "uid": "c1",
        "countdown": {"startDate": None, "endDate": None},
        "status": {"forceClose": False, "variations": [{"statusCard": "active", "title": "Ganhe 30% de bônus"}]},
    }  # fmt: skip
    card.update(overrides)
    return json.dumps({"props": {"pageProps": {"page": {"components": [{"props": card}]}}}})


def test_livelo_utc_end_is_converted_to_local_day():
    end_utc = "2026-11-11T02:59:00Z"
    local_day = datetime(2026, 11, 11, 2, 59, tzinfo=timezone.utc).astimezone().date()
    promotions = livelo.parse_offers(_card(countdown={"startDate": None, "endDate": end_utc}), NOW)
    assert promotions[0].end == local_day
    assert livelo._date("2026-11-10-23:59:00 GMT-03:00") == date(2026, 11, 10)


def test_livelo_force_closed_card_is_dropped():
    closed = {"forceClose": True, "variations": [{"statusCard": "active", "title": "Ganhe 30% de bônus"}]}
    assert livelo.parse_offers(_card(status=closed), NOW) == []
    assert len(livelo.parse_offers(_card(), NOW)) == 1


@pytest.mark.parametrize("payload", ["{}", '{"props": {"pageProps": {"page": {"components": []}}}}'])
def test_livelo_offers_rejects_page_without_components(payload):
    with pytest.raises(ValueError, match="formato esperado"):
        livelo.parse_offers(payload, NOW)


class _FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW


@pytest.fixture
def frozen_clock(monkeypatch):
    """Os collect() usam datetime.now(); fixá-lo em NOW impede que as fixtures vençam com o tempo."""
    for module in (livelo, esfera):
        monkeypatch.setattr(module, "datetime", _FrozenDatetime)


@pytest.mark.parametrize("blocked", ["Livelo (parceiros)", "Livelo (ofertas)"])
def test_livelo_pages_fail_independently(frozen_clock, window, tmp_path, blocked):
    # Cada página é uma fonte no pipeline: o bloqueio de uma não apaga as promoções da outra.
    pages = livelo.livelo_sources(None, LiveloSelectors(partners_url="p", offers_url="o"))
    contents = {"Livelo (parceiros)": "livelo_partners.json", "Livelo (ofertas)": "livelo_offers.json"}
    for page in pages:
        async def next_data(name=page.name):
            if name == blocked:
                raise SourceBlocked(f"{name} recusou o acesso automatizado (HTTP 403).")
            return fixture(contents[name])

        page._next_data = next_data
    report = asyncio.run(run_pipeline([window], Sources([], pages, None), tmp_path, NOW.date()))
    expected = {"Livelo (parceiros)": 5, "Livelo (ofertas)": 3}[blocked]  # as promoções da outra página
    assert report.promotions_by_source == {"Livelo": expected}
    assert len(report.failures) == 1 and blocked in report.failures[0]


def test_livelo_empty_next_data_is_an_error():
    class EmptyPage:
        async def goto(self, *_, **__):
            return None

        def locator(self, _):
            class Script:
                async def text_content(self):
                    return ""
            return Script()

    class FakeBrowser:
        @asynccontextmanager
        async def page(self):
            yield EmptyPage()

    source = livelo.livelo_sources(FakeBrowser(), LiveloSelectors(partners_url="p", offers_url="o"))[1]
    with pytest.raises(ValueError, match="__NEXT_DATA__"):
        asyncio.run(source.collect())


def test_esfera_keeps_pages_read_before_a_failure(frozen_clock):
    source = esfera.EsferaSource(None, EsferaSelectors(campaigns_api="api"))
    page_one = json.loads(fixture("esfera_campaigns.json"))
    for campaign in page_one["content"]:
        campaign["deadline"] = "2099-01-01T00:00:00"  # todas fora da janela, menos a que segue
    page_one["content"].append({"partnerName": "Polishop", "startDate": "2026-11-09T00:00:00",
                                "deadline": "2026-12-01T00:00:00", "partnerParity": 10})  # fmt: skip
    calls = []

    async def fetch(page_number):
        calls.append(page_number)
        if page_number:
            raise RuntimeError("HTTP 500")
        return json.dumps(page_one)

    source._fetch = fetch
    promotions = asyncio.run(source.collect())
    assert calls == [0, 1]
    assert [p.partner for p in promotions] == ["Polishop"]


def test_esfera_first_page_failure_is_reported():
    source = esfera.EsferaSource(None, EsferaSelectors(campaigns_api="api"))

    async def fetch(page_number):
        raise RuntimeError("HTTP 500")

    source._fetch = fetch
    with pytest.raises(RuntimeError):
        asyncio.run(source.collect())


@pytest.mark.parametrize(
    ("title", "programs", "kind"),
    [
        ("Iberia oferece 50% de desconto na compra de Avios", "Iberia Plus", "Compra de pontos"),
        ("Qatar vende Avios com 40% de bônus", "Qatar Privilege Club", "Notícia"),
        ("Compra de Avios com 35% de desconto", "", "Compra de pontos"),
    ],
)
def test_avios_alone_does_not_identify_a_program(title, programs, kind):
    assert (", ".join(feeds._programs(title)), infer_kind(title)) == (programs, kind)


def test_feed_source_reads_every_url_and_skips_repeated_links(monkeypatch):
    monkeypatch.setattr(feeds, "datetime", _FrozenDatetime)
    selectors = FeedSelectors(name="Blog", urls=["geral", "azul"], categories=["Promoções"])
    source = feeds.FeedSource(None, selectors)
    fetched = []

    async def fetch(url):
        fetched.append(url)
        return RSS  # o mesmo conteúdo nos dois feeds: cada notícia deve entrar uma vez

    source._fetch = fetch
    promotions = asyncio.run(source.collect())
    assert fetched == ["geral", "azul"]
    assert [p.link for p in promotions] == ["https://blog/1", "https://blog/3"]


def _feed_source(monkeypatch, urls, contents, categories=("Promoções",)):
    monkeypatch.setattr(feeds, "datetime", _FrozenDatetime)
    source = feeds.FeedSource(None, FeedSelectors(name="Blog", urls=urls, categories=list(categories)))

    async def fetch(url):
        content = contents[url]
        if isinstance(content, Exception):
            raise content
        return content

    source._fetch = fetch
    return source


def _rss(*items):
    body = "".join(
        f"<item><title>{title}</title><link>{link}</link><category>{category}</category>"
        "<pubDate>Tue, 10 Nov 2026 08:00:00 -0300</pubDate></item>"
        for title, link, category in items
    )
    return f"<rss><channel>{body}</channel></rss>"


@pytest.mark.parametrize("failing", ["primeiro", "ultimo"])
def test_feed_failure_keeps_the_other_feeds(monkeypatch, failing):
    contents = {
        "primeiro": _rss(("LATAM Pass oferece 25% de bônus", "https://blog/latam", "Promoções")),
        "ultimo": _rss(("Azul oferece 120% de bônus", "https://blog/azul", "Promoções")),
    }
    contents[failing] = SourceBlocked("Blog recusou o acesso automatizado (HTTP 403).")
    source = _feed_source(monkeypatch, ["primeiro", "ultimo"], contents)
    assert len(asyncio.run(source.collect())) == 1


def test_feed_errors_surface_when_every_feed_fails(monkeypatch):
    source = _feed_source(monkeypatch, ["a", "b"], {"a": RuntimeError("HTTP 500"), "b": "<rss><nao-fecha>"})
    with pytest.raises(Exception):
        asyncio.run(source.collect())


def test_feed_items_without_link_are_kept_when_titles_differ(monkeypatch):
    contents = {
        "a": _rss(("LATAM Pass oferece 25% de bônus", "", "Promoções")),
        "b": _rss(("Azul oferece 120% de bônus", "", "Promoções"), ("LATAM Pass oferece 25% de bônus", "", "Promoções")),
    }
    source = _feed_source(monkeypatch, ["a", "b"], contents)
    assert [p.program for p in asyncio.run(source.collect())] == ["LATAM Pass", "Azul Fidelidade"]


def test_ppv_program_feeds_are_not_filtered_by_parent_category(selectors):
    # Posts da subcategoria podem trazer só "LATAM Pass" ou "Azul Fidelidade", sem a categoria-pai.
    ppv = next(feed for feed in selectors.feeds if feed.name == "Pontos pra Voar")
    xml = _rss(
        ("LATAM Pass com 25% de bônus no Itaú", "https://ppv/1", "LATAM Pass"),
        ("Azul oferece 120% de bônus no Inter", "https://ppv/2", "Azul Fidelidade"),
        ("Mercado Livre libera cupons", "https://ppv/3", "Mercado Livre"),
    )
    assert [p.link for p in feeds.parse_feed(xml, ppv, NOW)] == ["https://ppv/1", "https://ppv/2"]


def test_feed_url_cannot_be_empty():
    with pytest.raises(ValueError):
        FeedSelectors(name="Blog", urls=[""])


# Colunas de categorização e dados quantitativos


def test_livelo_partner_quantitative_fields():
    adcos = livelo.parse_partners(fixture("livelo_partners.json"), NOW)[0]
    assert (adcos.unit, adcos.value, adcos.club_value, adcos.regular_value) == (
        "pontos por R$", Decimal("8"), Decimal("11"), Decimal("1")
    )
    assert (adcos.start_time, adcos.end_time) == ("00:00", "23:59")
    assert adcos.category == "wellness, saude, modaebeleza, perfumariaecosmeticos"  # sem "todos"
    assert adcos.rules.startswith("Campanha válida em 10/11/2026.")
    assert adcos.club_only is None  # o Clube ganha mais, mas a promoção não é exclusiva


def test_livelo_offer_reads_club_value_from_text():
    offers = livelo.parse_offers(fixture("livelo_offers.json"), NOW)
    black_friday = offers[0]
    assert (black_friday.unit, black_friday.club_value) == ("pontos por R$", Decimal("11"))
    assert offers[1].unit == "% de bônus"


def test_livelo_card_time_is_converted_from_utc():
    page = _card(countdown={"startDate": None, "endDate": "2026-11-11T02:59:00Z"})
    promotion = livelo.parse_offers(page, NOW)[0]
    assert promotion.end_time == f"{datetime(2026, 11, 11, 2, 59, tzinfo=timezone.utc).astimezone():%H:%M}"


def test_esfera_quantitative_fields():
    promotions, _ = esfera.parse_campaigns(fixture("esfera_campaigns.json"), NOW)
    nike = promotions[0]
    assert (nike.unit, nike.start_time, nike.end_time, nike.credit_days) == ("pontos por R$", "00:00", "23:59", 45)
    assert nike.rules == "Prazo para crédito de pontos é de 45 dias após a entrega do produto."
    assert nike.club_value is None  # clubClientParity 0: a campanha não tem valor para o clube


def test_feed_keeps_post_categories_and_unit():
    azul = feeds.parse_feed(RSS, feed(), NOW)[0]
    assert (azul.category, azul.unit) == ("Promoções, Transferência de pontos", "% de bônus")


@pytest.mark.parametrize(
    ("benefit", "unit"),
    [
        ("até 120% de bônus", "% de bônus"),
        ("Bonificação até 25%", "% de bônus"),
        ("Desconto até 50%", "% de desconto"),
        ("Até 15% OFF", "% de desconto"),
        ("até 16 pontos por real", "pontos por R$"),
        ("8 pontos a cada 1 real para clientes em geral", "pontos por R$"),
        ("Pontuação até 30", "pontos por R$"),
        ("3 milhas por dólar", "pontos por US$"),
        ("50.000 pontos", "pontos"),
        ("Bônus ou desconto até 10.000", "pontos"),
        ("", ""),
    ],
)
def test_value_unit(benefit, unit):
    assert value_unit(benefit) == unit


@pytest.mark.parametrize(
    ("text", "club", "only"),
    [
        ("Ganhe 11 pontos por real com Clube Livelo e 10 pontos por real demais clientes", Decimal("11"), False),
        ("Ganhe 11 pontos por real gasto exclusivo para assinantes Clube Livelo", Decimal("11"), True),
        ("11 pontos por real exclusivo para assinantes Clube Livelo e 10 pontos por real demais clientes",
         Decimal("11"), False),
        ("Oferta não exclusiva do Clube Livelo", None, False),
        ("Oferta exclusiva do Clube Livelo, não válida para demais clientes", None, True),
        ("Exclusivo para assinantes do Clube Smiles; não assinantes não participam", None, True),
        ("Clube Livelo: 50% de bônus para assinantes e 30% de bônus para não assinantes", None, False),
        # Benefício para os demais e negação no mesmo texto: ambíguo, fica vazio.
        ("Oferta exclusiva do Clube Livelo: sem bônus para demais clientes", None, None),
        ("Oferta exclusiva do Clube Livelo: não há desconto para não assinantes", None, None),
        ("Oferta exclusiva do Clube Livelo: não oferece 10.000 pontos para demais clientes", None, None),
        ("Não perca 11 pontos por real exclusivo para assinantes Clube Livelo e 10 pontos por real demais clientes",
         Decimal("11"), False),
        ("10 pontos por real para clientes em geral", None, None),
        ("Oferta exclusiva para assinantes do Clube Smiles", None, True),
        ("Livelo com 10 pontos por real", None, None),
    ],
)
def test_club_value_and_club_only_from_text(text, club, only):
    assert (club_value(text), club_only(text)) == (club, only)


def test_promotion_row_derives_quantitative_columns():
    promotion = Promotion(
        NOW, "Livelo", "Livelo", "Acúmulo de pontos", partner="ADCOS", value=Decimal("8"),
        regular_value=Decimal("3"), start=date(2026, 11, 2), end=date(2026, 11, 30), club_only=False,
        rules="Ganhe 11 pontos. Utilize o cupom LIVELO10. Consulte o regulamento.",
    )  # fmt: skip
    row = dict(zip(PROMOTION_COLUMNS, _promotion_row(promotion)))
    assert row["multiplicador"] == Decimal("2.67")
    assert (row["duracao_dias"], row["dias_restantes"]) == (29, 20)
    assert (row["cupom"], row["exclusivo_clube"]) == ("LIVELO10", "não")


def test_promotion_row_leaves_unknown_values_empty():
    promotion = Promotion(NOW, "Blog", "Smiles", "Notícia", title="Use o cupom de desconto da Smiles")
    row = dict(zip(PROMOTION_COLUMNS, _promotion_row(promotion)))
    assert [row[c] for c in ("multiplicador", "duracao_dias", "dias_restantes", "cupom", "exclusivo_clube")] == [
        None, None, None, "", ""
    ]


# Achados da revisão do Codex sobre as colunas


def test_livelo_partner_rate_in_dollars_per_two_units():
    page = json.loads(fixture("livelo_partners.json"))
    partner_list = next(
        c["props"] for c in page["props"]["pageProps"]["page"]["components"]
        if (c.get("props") or {}).get("ContentTypeUid") == "cb_partner_list"
    )  # fmt: skip
    partner_list["configPartners"][0]["parity"].update(currency="U$", currencyValue=2)
    adcos = livelo.parse_partners(json.dumps(page), NOW)[0]
    assert adcos.benefit.startswith("8 pontos por U$ 2")
    assert (adcos.unit, adcos.value, adcos.club_value, adcos.regular_value) == (
        "pontos por US$", Decimal("4"), Decimal("5.5"), Decimal("0.5")
    )


@pytest.mark.parametrize(
    ("title", "benefit", "value", "unit"),
    [
        ("Livelo: ganhe 3 pontos por US$ 1 na Amazon", "3 pontos por US$ 1", Decimal("3"), "pontos por US$"),
        ("Esfera: ganhe 3 pontos a cada 2 reais", "3 pontos a cada 2 reais", Decimal("1.5"), "pontos por R$"),
        ("Smiles: 5 milhas por dólar no Ponto Frio", "5 milhas por dólar", Decimal("5"), "pontos por US$"),
        ("Livelo oferece 104 mil pontos na assinatura", "104 mil pontos", Decimal("104000"), "pontos"),
    ],
)
def test_feed_keeps_currency_and_denominator_of_the_rate(title, benefit, value, unit):
    promotion = feeds.parse_feed(_rss((title, "https://blog/x", "Promoções")), feed(), NOW)[0]
    assert (promotion.benefit, promotion.value, promotion.unit) == (benefit, value, unit)


def test_livelo_offer_keeps_currency_of_the_rate():
    card = {"statusCard": "active", "title": "Ganhe 3 pontos por US$ 1 na loja"}
    page = _card(status={"forceClose": False, "variations": [card]})
    promotion = livelo.parse_offers(page, NOW)[0]
    assert (promotion.value, promotion.unit) == (Decimal("3"), "pontos por US$")


def test_esfera_club_rate_from_text_when_numeric_field_is_zero():
    promotions, _ = esfera.parse_campaigns(fixture("esfera_campaigns.json"), NOW)
    hoteis = next(p for p in promotions if p.partner == "Hoteis.com")
    assert (hoteis.value, hoteis.club_value) == (Decimal("3"), Decimal("4"))


def test_feed_last_day_has_no_known_duration():
    last_day = feeds.parse_feed(RSS, feed(), NOW)[1]
    row = dict(zip(PROMOTION_COLUMNS, _promotion_row(last_day)))
    assert (row["publicado_em"], row["inicio"], row["fim"]) == ("2026-11-10", None, "2026-11-10")
    assert (row["duracao_dias"], row["dias_restantes"]) == (None, 0)


@pytest.mark.parametrize(
    ("rules", "description", "coupon"),
    [
        ("NAO E NECESSARIO CUPOM PARA PONTUAR", "", ""),
        ("Use CUPOM DESCONTO na compra", "", ""),
        ("Compra sem cupom LIVELO10 não pontua", "", "LIVELO10"),  # o código é obrigatório
        ("Não perca: use o cupom LIVELO10", "", "LIVELO10"),
        ("Dispensa o uso de cupom LIVELO10", "", ""),
        ("Esta oferta não dispensa cupom LIVELO10", "", "LIVELO10"),
        ("Não dispensa o uso de cupom LIVELO10", "", "LIVELO10"),
        ("Não é dispensado o uso de cupom LIVELO10", "", "LIVELO10"),
        ("Uso de cupom LIVELO10 dispensado", "", "LIVELO10"),  # a dispensa vem depois: não dá para saber
        ("É dispensado o uso de cupom LIVELO10", "", ""),
        ("É dispensável o uso de cupom LIVELO10", "", ""),
        ("É indispensável o uso de cupom LIVELO10", "", "LIVELO10"),
        ("E indispensavel o uso de cupom LIVELO10", "", "LIVELO10"),
        ("Não é necessário cupom LIVELO10", "", ""),
        ("Sem necessidade de cupom LIVELO10", "", ""),
        ("Não precisa usar cupom PARA ganhar", "", ""),
        ("Não é necessário cupom.", "Use o cupom: BLACK10", "BLACK10"),
        ("Utilize o cupom LIVELO. Consulte o regulamento.", "cupom OUTRO", "LIVELO"),
    ],
)
def test_coupon_ignores_negation_and_common_words(rules, description, coupon):
    promotion = Promotion(NOW, "Livelo", "Livelo", "Acúmulo de pontos", rules=rules, description=description)
    assert dict(zip(PROMOTION_COLUMNS, _promotion_row(promotion)))["cupom"] == coupon
