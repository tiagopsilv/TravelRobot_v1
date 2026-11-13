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
from travelrobot.sources._promo_text import club_only, club_value, infer_kind, parse_benefit

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
        categories = list(dict.fromkeys(filter(None, ((c.text or "").strip() for c in item.findall("category")))))
        if selectors.categories and not set(categories) & set(selectors.categories):
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
        benefit, value, unit = parse_benefit(title)
        promotions.append(
            Promotion(
                executed_at=now,
                source=selectors.name,
                program=", ".join(programs),
                kind=infer_kind(title),
                title=title,
                benefit=benefit,
                value=value,
                published=published.date(),  # a data da notícia, não o início da campanha
                end=end,
                link=(item.findtext("link") or "").strip(),
                category=", ".join(categories),
                unit=unit,
                club_value=club_value(title),
                club_only=club_only(title),
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
        """Lê os feeds do blog um a um; a mesma notícia em dois feeds (geral e de um programa) entra uma vez.

        Um feed que falha não apaga os outros: a falha vai para o log e a coleta segue. Só quando
        todos falham o erro sobe para o relatório da execução.
        """
        now = datetime.now()
        promotions, seen, errors = [], set(), []
        for url in self._selectors.urls:
            try:
                xml = await with_retry(lambda: self._fetch(url), self.name)
                items = parse_feed(xml, self._selectors, now)
            except Exception as error:
                logger.warning("%s: o feed %s falhou: %s", self.name, url, error)
                errors.append(error)
                continue
            for promotion in items:
                key = promotion.link or promotion.title  # sem link, a notícia é identificada pelo título
                if key not in seen:
                    seen.add(key)
                    promotions.append(promotion)
        if errors and len(errors) == len(self._selectors.urls):
            raise errors[-1]
        return promotions

    async def _fetch(self, url: str) -> str:
        async with self._browser.page() as page:
            response = await page.request.get(url)
            raise_if_blocked(response, self.name)
            if not response.ok:
                raise RuntimeError(f"{self.name}: HTTP {response.status}")
            return await response.text()
