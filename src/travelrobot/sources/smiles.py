from __future__ import annotations

import logging
import re
from datetime import datetime
from urllib.parse import urljoin

from bs4 import Tag

from travelrobot.browser import Browser, raise_if_blocked, with_retry
from travelrobot.config import SmilesSelectors
from travelrobot.models import Promotion
from travelrobot.sources._html import attr_of, soup, text_of

logger = logging.getLogger(__name__)


def parse_promotions(html: str, selectors: SmilesSelectors, now: datetime) -> list[Promotion]:
    promotions = []
    for card in soup(html).select(selectors.card):
        title = text_of(card, selectors.title)
        if not title:
            logger.debug("Smiles: card sem título ignorado")
            continue
        validity = text_of(card, selectors.validity) or ""
        href = card.get("href")
        promotions.append(
            Promotion(
                executed_at=now,
                program="Smiles",
                type=_parse_type(card, selectors),
                title=title,
                text=text_of(card, selectors.text) or "",
                validity=re.sub(r"(?i)^válido até:?\s*", "", validity),
                link=urljoin(selectors.url, href) if href else "",
            )
        )
    return promotions


def _parse_type(card: Tag, selectors: SmilesSelectors) -> str:
    """O tipo costuma ser uma imagem: ".../BUSCAR_VOOS.png/f7b0?t=1" vira "Buscar Voos"."""
    text = text_of(card, selectors.type)
    if text:
        return text
    source = attr_of(card, f"{selectors.type} img", "src") or ""
    match = re.search(r"([^/]+)\.(?:png|jpe?g|svg|webp)", source, re.IGNORECASE)
    return re.sub(r"[_+]", " ", match.group(1)).title() if match else ""


class SmilesSource:
    def __init__(self, browser: Browser, selectors: SmilesSelectors) -> None:
        self._browser = browser
        self._selectors = selectors

    async def collect(self) -> list[Promotion]:
        html = await with_retry(self._fetch, "Smiles")
        return parse_promotions(html, self._selectors, datetime.now())

    async def _fetch(self) -> str:
        async with self._browser.page() as page:
            response = await page.goto(self._selectors.url, wait_until="domcontentloaded")
            raise_if_blocked(response, "Smiles")
            await page.wait_for_selector(self._selectors.card, state="attached")
            return await page.content()
