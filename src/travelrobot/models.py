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
    """Uma promoção de pontos ou milhas, vinda do próprio programa ou de um agregador."""

    executed_at: datetime
    source: str
    program: str
    kind: str
    partner: str | None = None
    title: str = ""
    description: str = ""
    benefit: str = ""  # como o site descreve: "Bonificação até 120%"
    value: Decimal | None = None  # o número do benefício, para ordenar e filtrar
    start: date | None = None
    end: date | None = None
    link: str = ""
    category: str = ""  # categoria do site (Smiles, parceiros Livelo) ou do post (blogs)
    unit: str = ""  # o que "value" mede: "pontos por R$", "% de bônus", "% de desconto", "pontos"
    club_value: Decimal | None = None  # o mesmo benefício para assinantes do clube do programa
    regular_value: Decimal | None = None  # o benefício fora da promoção, para medir o ganho
    club_only: bool | None = None  # None quando a fonte não informa
    start_time: str = ""  # "HH:MM", no horário local
    end_time: str = ""
    credit_days: int | None = None  # prazo para os pontos caírem na conta
    rules: str = ""  # trecho do regulamento que a fonte entrega
    published: date | None = None  # data do post, nos blogs; não é o início da campanha


@dataclass(slots=True)
class RunReport:
    promotions: int = 0
    promotions_by_source: dict[str, int] = field(default_factory=dict)
    offers: int = 0
    offers_by_source: dict[str, int] = field(default_factory=dict)
    hotels_with_reviews: int = 0
    hotels_with_distance: int = 0
    hotels: int = 0
    failures: list[str] = field(default_factory=list)
