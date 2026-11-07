from __future__ import annotations

from decimal import Decimal
from urllib.parse import quote

from travelrobot.browser import Browser, raise_if_blocked, with_retry
from travelrobot.config import GoogleMapsSelectors
from travelrobot.parsing import parse_distance_km
from travelrobot.sources._html import soup, text_of


def build_url(origin: str, destination: str) -> str:
    return f"https://www.google.com/maps/dir/{quote(origin, safe='')}/{quote(destination, safe='')}/?hl=pt-BR"


def parse_distance(html: str, selectors: GoogleMapsSelectors) -> Decimal | None:
    return parse_distance_km(text_of(soup(html), selectors.distance))


class GoogleMapsSource:
    def __init__(self, browser: Browser, selectors: GoogleMapsSelectors) -> None:
        self._browser = browser
        self._selectors = selectors

    async def distance_km(self, address: str, reference_point: str) -> Decimal | None:
        html = await with_retry(
            lambda: self._fetch(build_url(address, reference_point)), f"Maps {address}"
        )
        return parse_distance(html, self._selectors)

    async def _fetch(self, url: str) -> str:
        async with self._browser.page() as page:
            response = await page.goto(url, wait_until="commit")
            raise_if_blocked(response, "Google Maps")
            await page.wait_for_selector(self._selectors.distance, state="attached")
            return await page.content()
