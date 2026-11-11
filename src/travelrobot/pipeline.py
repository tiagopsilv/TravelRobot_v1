from __future__ import annotations

import asyncio
import logging
from collections import Counter
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Protocol, TypeVar

from travelrobot.models import GuestReviews, HotelOffer, Promotion, RunReport, SearchWindow
from travelrobot.parsing import normalize_name
from travelrobot.storage import save_hotels, save_promotions

logger = logging.getLogger(__name__)
T = TypeVar("T")
HotelKey = tuple[str, str]


class OfferSource(Protocol):
    name: str

    async def collect(self, window: SearchWindow) -> list[HotelOffer]: ...


class PromotionSource(Protocol):
    name: str

    async def collect(self) -> list[Promotion]: ...


class DistanceSource(Protocol):
    async def distance_km(self, address: str, reference_point: str) -> Decimal | None: ...


@dataclass(slots=True)
class Sources:
    offers: list[OfferSource]
    promotions: list[PromotionSource]
    distances: DistanceSource


def _hotel_key(offer: HotelOffer) -> HotelKey:
    return offer.city_name, normalize_name(offer.hotel_name)


def deduplicate(offers: list[HotelOffer]) -> list[HotelOffer]:
    """Mantém a primeira oferta de cada combinação de site, hotel e datas."""
    unique: dict[tuple, HotelOffer] = {}
    for offer in offers:
        key = (*_hotel_key(offer), offer.source, offer.check_in, offer.check_out)
        unique.setdefault(key, offer)
    return list(unique.values())


def share_hotel_details(offers: list[HotelOffer]) -> None:
    """Ofertas de fontes sem endereço ou avaliações aproveitam os dados do mesmo hotel em outra fonte."""
    addresses: dict[HotelKey, str] = {}
    reviews: dict[HotelKey, GuestReviews] = {}
    for offer in offers:
        if offer.address:
            addresses.setdefault(_hotel_key(offer), offer.address)
        if offer.reviews:
            reviews.setdefault(_hotel_key(offer), offer.reviews)
    for offer in offers:
        offer.address = offer.address or addresses.get(_hotel_key(offer))
        offer.reviews = offer.reviews or reviews.get(_hotel_key(offer))


async def _guarded(
    operation: Callable[[], Awaitable[T]], description: str, report: RunReport
) -> T | None:
    """Isola a falha de uma etapa: ela é registrada no relatório e a execução continua."""
    try:
        return await operation()
    except Exception as error:
        logger.exception("%s falhou", description)
        report.failures.append(f"{description}: {error}")
        return None


async def _collect_offers(
    windows: list[SearchWindow], sources: Sources, report: RunReport
) -> list[HotelOffer]:
    async def collect(source: OfferSource, window: SearchWindow) -> list[HotelOffer]:
        description = f"{source.name} ({window.city_name}, {window.check_in})"
        return await _guarded(lambda: source.collect(window), description, report) or []

    tasks = [collect(source, window) for source in sources.offers for window in windows]
    results = await asyncio.gather(*tasks)
    return deduplicate([offer for offers in results for offer in offers])


async def _add_distances(
    offers: list[HotelOffer],
    references: dict[str, str],
    sources: Sources,
    report: RunReport,
) -> None:
    hotels = {_hotel_key(offer): offer for offer in reversed(offers) if offer.address}

    async def fetch(key: HotelKey, offer: HotelOffer) -> tuple[HotelKey, Decimal | None]:
        reference = references[offer.city_name]
        operation = lambda: sources.distances.distance_km(offer.address, reference)  # noqa: E731
        return key, await _guarded(operation, f"Distância de {offer.hotel_name}", report)

    results = await asyncio.gather(*(fetch(key, offer) for key, offer in hotels.items()))
    found = {key: distance for key, distance in results if distance is not None}
    report.hotels_with_distance = len(found)
    for offer in offers:
        offer.distance_km = found.get(_hotel_key(offer), offer.distance_km)


async def run_pipeline(
    windows: list[SearchWindow], sources: Sources, output_dir: Path, run_date: date
) -> RunReport:
    """Executa a coleta e regrava os arquivos após cada etapa, preservando o trabalho já feito."""
    report = RunReport()

    logger.info("Etapa 1/3: promoções")
    results = await asyncio.gather(
        *(_guarded(source.collect, f"Promoções {source.name}", report) for source in sources.promotions)
    )
    promotions = [promotion for found in results for promotion in found or []]
    report.promotions = len(promotions)
    report.promotions_by_source = dict(Counter(promotion.source for promotion in promotions))
    if promotions:
        save_promotions(promotions, output_dir, run_date)

    logger.info("Etapa 2/3: ofertas e avaliações de hotéis")
    offers = await _collect_offers(windows, sources, report)
    share_hotel_details(offers)
    report.offers = len(offers)
    report.hotels = len({_hotel_key(offer) for offer in offers})
    report.hotels_with_reviews = len({_hotel_key(offer) for offer in offers if offer.reviews})
    report.offers_by_source = dict(Counter(offer.source for offer in offers))
    if not offers:
        logger.warning("Nenhuma oferta coletada.")
        return report
    save_hotels(offers, output_dir, run_date)

    logger.info("Etapa 3/3: distâncias de %d hotéis", report.hotels)
    references = {window.city_name: window.reference_point for window in windows}
    await _add_distances(offers, references, sources, report)
    save_hotels(offers, output_dir, run_date)

    return report
