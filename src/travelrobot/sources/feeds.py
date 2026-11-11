"""Notícias de promoções publicadas pelos blogs de milhas nos seus feeds RSS.

O feed traz título, data e link, mas não a validade. Por isso o robô só considera as notícias
recentes (FeedSelectors.max_age_days) e deduz do título o programa, o tipo e o benefício.
Os blogs têm direitos reservados: o CSV guarda título e link, para consulta.
"""
from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ElementTree
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

from travelrobot.browser import Browser, raise_if_blocked, with_retry
from travelrobot.config import FeedSelectors
from travelrobot.models import Promotion
from travelrobot.sources._promo_text import benefit_value, extract_benefit, infer_kind

logger = logging.getLogger(__name__)

# Nome canônico → como aparece nos títulos. A ordem no título é a ordem na coluna "programa".
PROGRAMS = {
    "Smiles": r"smiles",
    "LATAM Pass": r"latam\s*pass",
    "Azul Fidelidade": r"azul(?:\s+fidelidade)?|tudoazul",
    "Livelo": r"livelo",
    "Esfera": r"esfera",
    "Átomos (C6)": r"átomos",
    "Itaú": r"itaú|iupp",
    "Nubank": r"nubank",
    "KMV": r"km\s+de\s+vantagens|\bkmv\b",
    "Dotz": r"dotz",
    "ALL Accor": r"all\s+accor",
    "TAP Miles&Go": r"miles\s*&\s*go|\btap\b",
    "Flying Blue": r"flying\s+blue",
    "Qatar Privilege Club": r"privilege\s+club|qatar",
    "Emirates Skywards": r"skywards|emirates",
    "Iberia Plus": r"iberia",
    # "Avios" é a moeda de vários programas (Iberia, Qatar, British); sozinho não identifica nenhum.
    "British Airways": r"british\s+airways|executive\s+club",
    "American AAdvantage": r"aadvantage",
}
_PROGRAMS = [(name, re.compile(rf"(?<!\w)(?:{pattern})(?!\w)", re.IGNORECASE)) for name, pattern in PROGRAMS.items()]
_LAST_DAY = re.compile(r"último\s+dia|só\s+hoje|termina\s+hoje|acaba\s+hoje", re.IGNORECASE)


def parse_feed(xml: str, selectors: FeedSelectors, now: datetime) -> list[Promotion]:
    """Notícias recentes, das categorias escolhidas, que citam algum programa de fidelidade."""
    oldest = now - timedelta(days=selectors.max_age_days)
    promotions = []
    for item in ElementTree.fromstring(xml).iter("item"):
        title = " ".join((item.findtext("title") or "").split())
        categories = {(category.text or "").strip() for category in item.findall("category")}
        if selectors.categories and not categories & set(selectors.categories):
            continue
        published = _published(item.findtext("pubDate"))
        if published is None or published < oldest:
            continue
        programs = _programs(title)
        if not programs:
            continue
        end = published.date() if _LAST_DAY.search(title) else None
        if end and end < now.date():
            continue
        benefit = extract_benefit(title)
        promotions.append(
            Promotion(
                executed_at=now,
                source=selectors.name,
                program=", ".join(programs),
                kind=infer_kind(title),
                title=title,
                benefit=benefit,
                value=benefit_value(benefit),
                start=published.date(),
                end=end,
                link=(item.findtext("link") or "").strip(),
            )
        )
    return promotions


def _published(value: str | None) -> datetime | None:
    """A data do RSS tem fuso; o robô compara no horário local, sem fuso."""
    try:
        return parsedate_to_datetime(value).astimezone().replace(tzinfo=None) if value else None
    except (TypeError, ValueError):
        return None


def _programs(title: str) -> list[str]:
    found = sorted((match.start(), name) for name, pattern in _PROGRAMS if (match := pattern.search(title)))
    return [name for _, name in found]


class FeedSource:
    def __init__(self, browser: Browser, selectors: FeedSelectors) -> None:
        self._browser = browser
        self._selectors = selectors
        self.name = selectors.name

    async def collect(self) -> list[Promotion]:
        xml = await with_retry(self._fetch, self.name)
        return parse_feed(xml, self._selectors, datetime.now())

    async def _fetch(self) -> str:
        async with self._browser.page() as page:
            response = await page.request.get(self._selectors.url)
            raise_if_blocked(response, self.name)
            if not response.ok:
                raise RuntimeError(f"{self.name}: HTTP {response.status}")
            return await response.text()
