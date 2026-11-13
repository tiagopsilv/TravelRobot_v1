"""Promoções da Smiles, lidas do JSON que a própria página de promoções baixa para montar os cartões.

O robô só abre a página pública; não chama a API diretamente, porque o robots.txt da Smiles
não permite URLs com parâmetros, e a API só funciona com eles.
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime
from urllib.parse import urljoin

from travelrobot.browser import Browser, raise_if_blocked, with_retry
from travelrobot.config import SmilesSelectors
from travelrobot.models import Promotion
from travelrobot.sources._html import soup
from travelrobot.sources._promo_text import infer_kind, parse_benefit

logger = logging.getLogger(__name__)

SOURCE = "Smiles"
ACTIVE = "Ativa"
# Códigos de categoria do JSON → nome legível.
CATEGORIES = {
    "milhas": "Milhas",
    "Servicos": "Serviços",
    "ClubeSmiles": "Clube Smiles",
    "CartaoGolSmiles": "Cartão Gol Smiles",
}


def parse_promotions(payload: str, selectors: SmilesSelectors, now: datetime) -> list[Promotion]:
    """Mantém as promoções ativas que ainda não acabaram; o JSON também traz centenas de encerradas."""
    items = [
        {
            field["name"]: (field.get("contentFieldValue") or {}).get("data") or ""
            for field in item.get("contentFields", [])
        }
        for item in json.loads(payload).get("items", [])
    ]
    if not any("PromocaoAtivaOuEncerrada" in fields for fields in items):
        # Outro JSON capturado no lugar, ou a Smiles mudou o formato: falhar é melhor que devolver zero.
        raise ValueError("Smiles: o JSON capturado não traz promoções no formato esperado.")
    promotions = []
    for fields in items:
        end = _date(fields.get("DataEncerramento"))
        if fields.get("PromocaoAtivaOuEncerrada") != ACTIVE or (end and end < now.date()):
            continue
        title = fields.get("TituloCard", "").strip()
        if not title:
            logger.debug("Smiles: promoção sem título ignorada (fim %s).", end)
            continue
        description = _plain_text(fields.get("FraseCard"))
        categories = [CATEGORIES.get(category, category) for category in _categories(fields.get("Categoria"))]
        text = f"{title} {description}"
        benefit, value, unit = parse_benefit(text)
        link = fields.get("LinkDaPromocao", "").strip()
        promotions.append(
            Promotion(
                executed_at=now,
                source=SOURCE,
                program="Smiles",
                kind=infer_kind(text, "Clubes" if "Clube Smiles" in categories else "Outras"),
                title=title,
                description=description,
                benefit=benefit,
                value=value,
                start=_date(fields.get("DataDeInicio")),
                end=end,
                link=urljoin(selectors.url, link) if link else "",
                category=", ".join(categories),
                unit=unit,
                club_only={"true": True, "false": False}.get(fields.get("ExclusivaClube", "")),
                start_time=_time(fields.get("HoraDeInicio")),
                end_time=_time(fields.get("HoraDeEncerramento")),
            )
        )
    return promotions


def _date(value: str | None) -> date | None:
    """"2026-11-15T00:00:00Z" vira 15/11/2026; a hora vem em outro campo (_time)."""
    try:
        return date.fromisoformat(value[:10]) if value else None
    except ValueError:
        return None


def _time(value: str | None) -> str:
    """"10:00" fica como está; um valor fora do formato vira vazio."""
    value = (value or "").strip()
    return value if len(value) == 5 and value[2] == ":" and value.replace(":", "").isdigit() else ""


def _plain_text(html: str | None) -> str:
    return " ".join(soup(html).get_text(" ", strip=True).split()) if html else ""


def _categories(value: str | None) -> list[str]:
    try:
        categories = json.loads(value) if value else []
    except json.JSONDecodeError:
        return [value]
    return [str(category) for category in categories] if isinstance(categories, list) else []


class SmilesSource:
    name = SOURCE

    def __init__(self, browser: Browser, selectors: SmilesSelectors) -> None:
        self._browser = browser
        self._selectors = selectors

    async def collect(self) -> list[Promotion]:
        payload = await with_retry(self._fetch, SOURCE)
        return parse_promotions(payload, self._selectors, datetime.now())

    async def _fetch(self) -> str:
        selectors = self._selectors
        async with self._browser.page() as page:
            async with page.expect_response(
                lambda response: selectors.promotions_response in response.url and response.ok
            ) as promotions:
                response = await page.goto(selectors.url, wait_until="domcontentloaded")
                raise_if_blocked(response, SOURCE)
            return await (await promotions.value).text()
