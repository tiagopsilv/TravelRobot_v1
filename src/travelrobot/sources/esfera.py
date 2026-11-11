"""Campanhas de acúmulo da Esfera, da mesma API que a página pública de campanhas usa.

A página esfera.com.vc/esfera-lp_campanhas pede as campanhas de 5 em 5. O robô faz o mesmo pedido
com páginas de 100 (são umas 300 em andamento), o que o robots.txt permite.

Boa parte das campanhas "em andamento" não é promoção: são a pontuação normal da loja ou ações
internas, com prazo em 2030, 2040 ou 2100. Promoções duram dias ou semanas, então só entram as
campanhas com duração de até MAX_DURATION.
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from urllib.parse import urlencode

from travelrobot.browser import Browser, raise_if_blocked, with_retry
from travelrobot.config import EsferaSelectors
from travelrobot.models import Promotion

logger = logging.getLogger(__name__)

SOURCE = "Esfera"
MAX_DURATION = timedelta(days=62)
PAGE_SIZE = 100
MAX_PAGES = 10


def parse_campaigns(payload: str, now: datetime) -> tuple[list[Promotion], bool]:
    """Devolve as promoções da página e se ela é a última."""
    data = json.loads(payload)
    if "content" not in data:
        raise ValueError("Esfera: a resposta não traz campanhas no formato esperado.")
    promotions = []
    for campaign in data["content"]:
        start, end = _date(campaign.get("startDate")), _date(campaign.get("deadline"))
        if start is None or end is None or end < now.date() or end - start > MAX_DURATION:
            continue
        partner = ((campaign.get("subPartner") or {}).get("subPartnerName") or campaign.get("partnerName") or "").strip()
        benefit = " · ".join(filter(None, [campaign.get("generalParity"), campaign.get("clubParity")]))
        rate = campaign.get("partnerParity")
        promotions.append(
            Promotion(
                executed_at=now,
                source=SOURCE,
                program="Esfera",
                kind="Acúmulo de pontos",
                partner=partner or None,
                title=(campaign.get("campaignName") or "").strip(),
                benefit=benefit,
                value=Decimal(str(rate)) if rate else None,
                start=start,
                end=end,
                link=campaign.get("urlPagePartner") or "",
            )
        )
    return promotions, bool(data.get("last", True))


def _date(value: str | None) -> date | None:
    try:
        return date.fromisoformat(value[:10]) if value else None
    except ValueError:
        return None


class EsferaSource:
    name = SOURCE

    def __init__(self, browser: Browser, selectors: EsferaSelectors) -> None:
        self._browser = browser
        self._selectors = selectors

    async def collect(self) -> list[Promotion]:
        now = datetime.now()
        promotions = []
        for page_number in range(MAX_PAGES):
            try:
                payload = await with_retry(lambda: self._fetch(page_number), SOURCE)
                page_promotions, last = parse_campaigns(payload, now)
            except Exception as error:
                if not page_number:
                    raise
                # Uma página posterior falhou: mantém as já lidas em vez de perder tudo.
                logger.warning(
                    "Esfera: a página %d falhou (%s); ficam as %d promoções já lidas.",
                    page_number + 1, error, len(promotions),
                )  # fmt: skip
                return promotions
            promotions += page_promotions
            if last:
                return promotions
        logger.warning("Esfera: parou em %d páginas; pode haver mais campanhas.", MAX_PAGES)
        return promotions

    async def _fetch(self, page_number: int) -> str:
        query = urlencode({"page": page_number, "size": PAGE_SIZE, "active": "true"})
        async with self._browser.page() as page:
            response = await page.request.get(f"{self._selectors.campaigns_api}?{query}")
            raise_if_blocked(response, SOURCE)
            if not response.ok:
                raise RuntimeError(f"{SOURCE}: HTTP {response.status}")
            return await response.text()
