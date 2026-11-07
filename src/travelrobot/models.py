from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class SearchWindow:
    city_name: str
    city_code: str
    text_for_search: str
    reference_point: str
    website_url: str
    check_in: date
    check_out: date

    @property
    def nights(self) -> int:
        return (self.check_out - self.check_in).days


@dataclass(slots=True)
class GuestReviews:
    """Resumo de avaliações do Google. O Google não dá nota por categoria, só temas com sentimento."""

    rating: Decimal | None = None
    review_count: int | None = None
    positive_topics: list[str] = field(default_factory=list)
    negative_topics: list[str] = field(default_factory=list)
    other_sites: list[str] = field(default_factory=list)


@dataclass(slots=True)
class HotelOffer:
    executed_at: datetime
    source: str
    city_name: str
    hotel_name: str
    check_in: date
    check_out: date
    price: Decimal
    currency: str | None = None
    rating: Decimal | None = None
    payment_conditions: str | None = None
    people: int | None = None
    address: str | None = None
    link: str | None = None
    html: str = ""
    distance_km: Decimal | None = None
    reviews: GuestReviews | None = None

    @property
    def nights(self) -> int:
        return (self.check_out - self.check_in).days


@dataclass(frozen=True, slots=True)
class Promotion:
    executed_at: datetime
    program: str
    type: str
    title: str
    text: str
    validity: str
    link: str


@dataclass(slots=True)
class RunReport:
    promotions: int = 0
    offers: int = 0
    offers_by_source: dict[str, int] = field(default_factory=dict)
    hotels_with_reviews: int = 0
    hotels_with_distance: int = 0
    hotels: int = 0
    failures: list[str] = field(default_factory=list)
