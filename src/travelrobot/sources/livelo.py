"""Promoções da Livelo, lidas dos dados que o próprio site entrega embutidos na página.

O site é Next.js: as páginas trazem o conteúdo em <script id="__NEXT_DATA__">. São lidas duas:
- a lista de parceiros, com os pontos por real de cada loja e as datas das promoções;
- a vitrine de ofertas, com os cartões de campanha (transferência bonificada, clube etc.), que
  descrevem o benefício só em texto.
"""
from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal

from travelrobot.browser import Browser, raise_if_blocked, with_retry
from travelrobot.config import LiveloSelectors
from travelrobot.models import Promotion
from travelrobot.sources._html import soup
from travelrobot.sources._promo_text import club_only, club_value, infer_kind, parse_benefit

logger = logging.getLogger(__name__)

SOURCE = "Livelo"
PARTNER_LIST = "cb_partner_list"
OFFER_CARD = "cb_previsibility"
# "2026-11-10-23:59:00 GMT-03:00": a hora dos parceiros já vem no horário de Brasília.
_PARTNER_TIME = re.compile(r"\d{4}-\d{2}-\d{2}[-T ](\d{2}:\d{2})")


def parse_partners(next_data: str, now: datetime) -> list[Promotion]:
    """Parceiros com promoção de acúmulo em vigor."""
    lists = [component for component in _components(next_data) if component.get("ContentTypeUid") == PARTNER_LIST]
    if not lists:
        raise ValueError("Livelo: a página de parceiros não traz a lista no formato esperado.")
    promotions = []
    for partner in lists[0].get("configPartners") or []:
        parity = partner.get("parity") or {}
        end = _date(parity.get("dateEnd"))
        if not parity.get("promotion") or (end and end < now.date()):
            continue
        rate, club, regular = parity.get("parity"), parity.get("parityClub"), parity.get("parityBau")
        currency, per_amount = parity.get("currency") or "R$", parity.get("currencyValue") or 1
        per = f"por {currency} {per_amount}"
        benefit = f"{rate} pontos {per}"
        if club and rate is not None and club > rate:
            benefit += f" ({club} no Clube Livelo)"
        if regular:
            benefit += f"; normal: {regular}"
        promotions.append(
            Promotion(
                executed_at=now,
                source=SOURCE,
                program="Livelo",
                kind="Acúmulo de pontos",
                partner=(partner.get("name") or "").strip() or None,
                title=f"{partner.get('name', '').strip()}: {rate} pontos {per}",
                benefit=benefit,
                value=_per_unit(rate, per_amount),
                start=_date(parity.get("dateStart")),
                end=end,
                link=partner.get("partnerDetailsPage") or partner.get("link") or "",
                category=_partner_categories(partner.get("categories")),
                unit="pontos por US$" if "U" in currency.upper() else "pontos por R$",
                club_value=_per_unit(club, per_amount),
                regular_value=_per_unit(regular, per_amount),
                start_time=_partner_time(parity.get("dateStart")),
                end_time=_partner_time(parity.get("dateEnd")),
                rules=_plain(parity.get("legalTerms")),
            )
        )
    return promotions


def parse_offers(next_data: str, now: datetime) -> list[Promotion]:
    """Cartões de campanha em vigor na vitrine de ofertas; o mesmo cartão aparece em várias abas."""
    if not _components(next_data):
        raise ValueError("Livelo: a página de ofertas não traz componentes no formato esperado.")
    promotions, seen = [], set()
    for card in _find(json.loads(next_data), OFFER_CARD):
        status = card.get("status") or {}
        active = next((v for v in status.get("variations") or [] if v.get("statusCard") == "active"), None)
        countdown = card.get("countdown") or {}
        end = _date(countdown.get("endDate"))
        if active is None or status.get("forceClose") or card.get("uid") in seen or (end and end < now.date()):
            continue
        seen.add(card.get("uid"))
        title = " ".join((active.get("title") or "").split())
        description = _plain(active.get("description"))
        text = f"{title} {description}"
        benefit, value, unit = parse_benefit(text)
        promotions.append(
            Promotion(
                executed_at=now,
                source=SOURCE,
                program="Livelo",
                kind=infer_kind(text),
                title=title,
                description=description,
                benefit=benefit,
                value=value,
                start=_date(countdown.get("startDate")),
                end=end,
                link=((active.get("button") or {}).get("redirectLink")) or "",
                unit=unit,
                club_value=club_value(text),
                club_only=club_only(text),
                start_time=_card_time(countdown.get("startDate")),
                end_time=_card_time(countdown.get("endDate")),
            )
        )
    return promotions


def _components(next_data: str) -> list[dict]:
    page = json.loads(next_data).get("props", {}).get("pageProps", {}).get("page") or {}
    return [component.get("props") or {} for component in page.get("components") or []]


def _find(node: object, content_type: str) -> Iterator[dict]:
    if isinstance(node, dict):
        if node.get("ContentTypeUid") == content_type:
            yield node
        for value in node.values():
            yield from _find(value, content_type)
    elif isinstance(node, list):
        for value in node:
            yield from _find(value, content_type)


def _date(value: str | None) -> date | None:
    """O dia no horário local da execução.

    Os cartões trazem instantes em UTC ("2026-11-11T02:59:00Z" é 10/11 às 23h59 em Brasília) e
    são convertidos. Os parceiros trazem "2026-11-10-23:59:00 GMT-03:00", já no horário de
    Brasília, e valem os 10 primeiros caracteres.
    """
    if not value:
        return None
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return moment.astimezone().date() if moment.tzinfo else moment.date()


def _card_time(value: str | None) -> str:
    """A hora dos cartões, convertida de UTC para o horário local, como em _date."""
    try:
        moment = datetime.fromisoformat(value) if value else None
    except ValueError:
        return ""
    if moment is None:
        return ""
    return f"{moment.astimezone() if moment.tzinfo else moment:%H:%M}"


def _partner_time(value: str | None) -> str:
    match = _PARTNER_TIME.match(value or "")
    return match[1] if match else ""


def _partner_categories(value: str | None) -> str:
    """"todos wellness saude" vira "wellness, saude": "todos" é a aba que lista todos os parceiros."""
    return ", ".join(category for category in (value or "").split() if category != "todos")


def _per_unit(points: object, per_amount: object) -> Decimal | None:
    """Pontos por 1 unidade da moeda: "8 pontos por U$ 2" vira 4, para comparar com as outras taxas."""
    if not isinstance(points, (int, float)) or isinstance(points, bool) or not points:
        return None
    amount = Decimal(str(per_amount)) if isinstance(per_amount, (int, float)) and per_amount else Decimal(1)
    return Decimal(str(points)) / amount


def _plain(html: str | None) -> str:
    return " ".join(soup(html).get_text(" ").split()) if html else ""


class _LiveloPage:
    """Uma página da Livelo; cada uma é uma fonte no pipeline, para que a falha de uma não apague a outra."""

    name: str

    def __init__(self, browser: Browser, url: str) -> None:
        self._browser = browser
        self._url = url

    async def collect(self) -> list[Promotion]:
        next_data = await with_retry(self._next_data, self.name)
        return self._parse(next_data, datetime.now())

    async def _next_data(self) -> str:
        async with self._browser.page() as page:
            response = await page.goto(self._url, wait_until="domcontentloaded")
            raise_if_blocked(response, self.name)
            next_data = await page.locator("script#__NEXT_DATA__").text_content()
        if not next_data:
            raise ValueError(f"{self.name}: a página não trouxe os dados embutidos (__NEXT_DATA__).")
        return next_data


class LiveloPartnersSource(_LiveloPage):
    name = "Livelo (parceiros)"
    _parse = staticmethod(parse_partners)


class LiveloOffersSource(_LiveloPage):
    name = "Livelo (ofertas)"
    _parse = staticmethod(parse_offers)


def livelo_sources(browser: Browser, selectors: LiveloSelectors) -> list[_LiveloPage]:
    return [LiveloPartnersSource(browser, selectors.partners_url), LiveloOffersSource(browser, selectors.offers_url)]
