"""Radar PPV: resumo diário do blog Pontos pra Voar com promoções de vários programas, em tabelas.

O post é lido pela API pública do WordPress do blog. O conteúdo tem direitos reservados:
serve para consulta, não para ser republicado.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime, timedelta
from urllib.parse import urlencode

from bs4 import Tag

from travelrobot.browser import Browser, raise_if_blocked, with_retry
from travelrobot.config import PontosPraVoarSelectors
from travelrobot.models import Promotion
from travelrobot.parsing import parse_decimal
from travelrobot.sources._html import soup
from travelrobot.sources._promo_text import value_unit

logger = logging.getLogger(__name__)

SOURCE = "Pontos pra Voar (Radar PPV)"
STALE_AFTER = timedelta(days=3)
# O Radar lista promoções correntes; validade a mais de 300 dias do post é uma linha antiga.
MAX_AHEAD = timedelta(days=300)
MONTHS = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)  # fmt: skip
_DAY_MONTH = re.compile(r"(\d{1,2})\s+de\s+([a-zç]+)", re.IGNORECASE)
_FOOTNOTE = re.compile(r"[¹²³⁴⁵⁶⁷⁸⁹⁰*]+")
_BENEFIT_HEADER = re.compile(r"\(\s*até\s*\)", re.IGNORECASE)
_HOUR = re.compile(r"\((\d{1,2})h(\d{2})?\)")


def latest_post(payload: str, selectors: PontosPraVoarSelectors) -> dict | None:
    """A busca do WordPress também devolve posts que só citam o Radar; vale o mais recente que é um."""
    posts = [
        post
        for post in json.loads(payload)
        if _plain(post["title"]["rendered"]).startswith(selectors.title_prefix)
    ]
    return max(posts, key=lambda post: post["date"], default=None)


def parse_post(html: str, published: date, now: datetime) -> list[Promotion]:
    promotions = []
    for table in soup(html).select("table"):
        heading = table.find_previous(["h2", "h3", "h4"])
        kind = re.sub(r"(?i)^promoções de\s+", "", _plain(heading.get_text(" ")) if heading else "")
        promotions += _parse_table(table, kind[:1].upper() + kind[1:], published, now)
    return promotions


def _parse_table(table: Tag, kind: str, published: date, now: datetime) -> list[Promotion]:
    rows = table.select("tr")
    if not rows:
        return []
    headers = [_plain(cell.get_text(" ")) for cell in rows[0].select("th, td")]
    columns = {_column(header): index for index, header in enumerate(headers)}
    if "program" not in columns or "benefit" not in columns:
        logger.warning("Radar PPV: tabela %r com colunas desconhecidas: %s", kind, headers)
        return []
    benefit_label = _BENEFIT_HEADER.sub("", headers[columns["benefit"]]).strip()

    promotions = []
    for row in rows[1:]:
        cells = row.select("td")
        if len(cells) != len(headers):
            continue
        text = {name: _plain(cells[index].get_text(" ")) for name, index in columns.items()}
        end = _end_date(text.get("validity", ""), published)
        if not text["program"] or (end and end < now.date()):
            continue
        value = _FOOTNOTE.sub("", text["benefit"])
        link = cells[columns["access"]].select_one("a[href]") if "access" in columns else None
        benefit = f"{benefit_label} até {value}" if value else ""
        hour = _HOUR.search(text.get("validity", ""))
        promotions.append(
            Promotion(
                executed_at=now,
                source=SOURCE,
                program=text["program"],
                kind=kind,
                partner=text.get("partner") or None,
                benefit=benefit,
                value=parse_decimal(value),
                unit=value_unit(benefit),
                end_time=f"{int(hour[1]):02d}:{hour[2] or '00'}" if hour and end else "",
                end=end,
                published=published,
                description=text.get("validity", "") if end is None else "",
                link=link["href"] if link else "",
            )
        )
    return promotions


def _column(header: str) -> str:
    lowered = header.lower()
    if _BENEFIT_HEADER.search(header):
        return "benefit"
    if lowered in ("programa", "clube"):
        return "program"
    return {"parceiro": "partner", "validade": "validity", "acesso": "access"}.get(lowered, header)


def _end_date(validity: str, published: date) -> date | None:
    """"30 de novembro (21h)" não traz o ano, então ele é deduzido da data do post.

    Regra: vale a primeira data a partir de 31 dias antes do post, desde que não passe de
    MAX_AHEAD depois dele. Uma data mais distante é tratada como linha antiga, e a função devolve a
    última ocorrência passada, que é descartada como vencida. Exemplos com post de 9/11/2026:
    "30 de novembro" → 30/11/2026; "15 de janeiro" → 15/01/2027; "1 de outubro" → 01/10/2026.
    """
    match = _DAY_MONTH.search(validity)
    if not match or match[2].lower() not in MONTHS:
        return None
    month, day = MONTHS.index(match[2].lower()) + 1, int(match[1])
    earliest = published - timedelta(days=31)
    previous = None
    for year in range(published.year - 4, published.year + 5):  # a faixa alcança um 29 de fevereiro
        try:
            end = date(year, month, day)
        except ValueError:
            continue
        if end < earliest:
            previous = end
        elif end - published <= MAX_AHEAD:
            return end
        else:
            return previous
    return previous


def _plain(text: str) -> str:
    return " ".join(soup(text).get_text(" ").split()) if "<" in text or "&" in text else " ".join(text.split())


class PontosPraVoarSource:
    name = SOURCE

    def __init__(self, browser: Browser, selectors: PontosPraVoarSelectors) -> None:
        self._browser = browser
        self._selectors = selectors

    async def collect(self) -> list[Promotion]:
        payload = await with_retry(self._fetch, SOURCE)
        post = latest_post(payload, self._selectors)
        if post is None:
            logger.warning("Radar PPV: nenhum post encontrado.")
            return []
        now = datetime.now()
        published = datetime.fromisoformat(post["date"])
        if now - published > STALE_AFTER:
            logger.warning("Radar PPV: o post mais recente é de %s.", f"{published:%d/%m/%Y}")
        logger.info("Radar PPV: lendo %s", post["link"])
        return parse_post(post["content"]["rendered"], published.date(), now)

    async def _fetch(self) -> str:
        query = urlencode(
            {"search": self._selectors.title_prefix, "per_page": 5, "_fields": "date,link,title,content"}
        )
        async with self._browser.page() as page:
            response = await page.request.get(f"{self._selectors.posts_api}?{query}")
            raise_if_blocked(response, SOURCE)
            if not response.ok:
                raise RuntimeError(f"{SOURCE}: HTTP {response.status}")
            return await response.text()
