from __future__ import annotations

import logging
from datetime import datetime

from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from travelrobot.browser import Browser, raise_if_blocked, with_retry
from travelrobot.config import DecolarSelectors
from travelrobot.models import HotelOffer, SearchWindow
from travelrobot.parsing import parse_currency, parse_decimal, parse_int
from travelrobot.sources._html import soup, text_of

logger = logging.getLogger(__name__)


def build_url(window: SearchWindow, page: int) -> str:
    return (
        f"{window.website_url.rstrip('/')}/accommodations/results/{window.city_code}/"
        f"{window.check_in:%Y-%m-%d}/{window.check_out:%Y-%m-%d}/?page={page}"
    )


def parse_results(
    html: str, window: SearchWindow, selectors: DecolarSelectors, now: datetime
) -> list[HotelOffer]:
    offers = []
    for card in soup(html).select(selectors.result):
        name = text_of(card, selectors.name)
        price_text = text_of(card, selectors.price)
        price = parse_decimal(price_text)
        if not name or price is None:
            logger.debug("Decolar: card sem nome ou preço ignorado")
            continue
        offers.append(
            HotelOffer(
                executed_at=now,
                source="Decolar",
                city_name=window.city_name,
                hotel_name=name,
                check_in=window.check_in,
                check_out=window.check_out,
                price=price,
                currency=parse_currency(price_text),
                rating=parse_decimal(text_of(card, selectors.rating)),
                payment_conditions=text_of(card, selectors.payment_conditions),
                people=_parse_people(text_of(card, selectors.people)),
                html=str(card),
            )
        )
    return offers


def _parse_people(text: str | None) -> int | None:
    """"1 noite, 2 pessoas" vira 2: o número de pessoas vem depois da vírgula."""
    return parse_int(text.split(",", 1)[1]) if text and "," in text else None


class DecolarSource:
    name = "Decolar"

    def __init__(
        self, browser: Browser, selectors: DecolarSelectors, max_pages: int
    ) -> None:
        self._browser = browser
        self._selectors = selectors
        self._max_pages = max_pages

    async def collect(self, window: SearchWindow) -> list[HotelOffer]:
        if not window.city_code:
            logger.warning("Decolar: %s não tem city_code; busca ignorada.", window.city_name)
            return []

        offers: list[HotelOffer] = []
        for number in range(1, self._max_pages + 1):
            url = build_url(window, number)
            html = await with_retry(lambda: self._fetch(url), f"Decolar {url}")
            page_offers = parse_results(html, window, self._selectors, datetime.now())
            if not page_offers:
                break
            offers.extend(page_offers)
        return offers

    async def _fetch(self, url: str) -> str:
        async with self._browser.page() as page:
            response = await page.goto(url, wait_until="domcontentloaded")
            raise_if_blocked(response, "Decolar")
            try:
                await page.wait_for_selector(self._selectors.result)
            except PlaywrightTimeoutError:
                logger.debug("Decolar: nenhum resultado em %s", url)
            return await page.content()
