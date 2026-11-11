from __future__ import annotations

import tomllib
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class ConfigError(Exception):
    """Configuração ausente ou inválida."""


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Settings(_Strict):
    output_dir: Path = Path("output")
    log_dir: Path = Path("logs")
    headless: bool = True
    concurrency: int = Field(default=4, ge=1, le=16)
    timeout_seconds: int = Field(default=30, ge=1)
    decolar_max_pages: int = Field(default=25, ge=1)


class SearchRule(_Strict):
    enabled: bool = True
    city_name: str = Field(min_length=1)
    city_code: str = ""
    text_for_search: str = Field(min_length=1)
    reference_point: str = Field(min_length=1)
    start_date: date | Literal["today"]
    end_date: date | Literal["end_of_month", "end_of_year"]
    range_type: Literal["single", "weekly"] = "single"
    website_url: str = "https://www.decolar.com"


class DecolarSelectors(_Strict):
    result: str
    name: str
    rating: str
    payment_conditions: str
    people: str
    price: str


class GoogleHotelsSelectors(_Strict):
    check_in_input: str
    check_out_input: str
    hotel_card: str
    hotel_link: str
    hotel_name: str
    hotel_rating: str
    prices_tab: str
    offer: str
    offer_price: str
    offer_site: str
    offer_link: str
    address: str
    reviews_tab: str
    reviews_block: str
    reviews_summary: str
    topic_button: str
    topic_label: str
    topic_positive_class: str
    topic_negative_class: str
    other_site: str
    other_site_name: str
    other_site_score: str


class GoogleMapsSelectors(_Strict):
    distance: str


class SmilesSelectors(_Strict):
    url: str
    promotions_response: str


class PontosPraVoarSelectors(_Strict):
    posts_api: str
    title_prefix: str


class LiveloSelectors(_Strict):
    partners_url: str
    offers_url: str


class EsferaSelectors(_Strict):
    campaigns_api: str


class FeedSelectors(_Strict):
    name: str = Field(min_length=1)
    url: str = Field(min_length=1)
    # Só entram notícias com alguma destas categorias do feed; vazio aceita todas.
    categories: list[str] = []
    max_age_days: int = Field(default=3, ge=1)


class Selectors(_Strict):
    decolar: DecolarSelectors
    google_hotels: GoogleHotelsSelectors
    google_maps: GoogleMapsSelectors
    smiles: SmilesSelectors
    pontos_pra_voar: PontosPraVoarSelectors
    livelo: LiveloSelectors
    esfera: EsferaSelectors
    feeds: list[FeedSelectors] = []


class AppConfig(_Strict):
    settings: Settings = Settings()
    search: list[SearchRule]


def _read_toml(path: Path) -> dict:
    try:
        with path.open("rb") as file:
            return tomllib.load(file)
    except FileNotFoundError as error:
        raise ConfigError(f"Arquivo não encontrado: {path}") from error
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"TOML inválido em {path}: {error}") from error


def load_config(path: Path) -> AppConfig:
    try:
        return AppConfig.model_validate(_read_toml(path))
    except ValidationError as error:
        raise ConfigError(f"Configuração inválida em {path}:\n{error}") from error


def load_selectors(path: Path) -> Selectors:
    try:
        return Selectors.model_validate(_read_toml(path))
    except ValidationError as error:
        raise ConfigError(f"Seletores inválidos em {path}:\n{error}") from error
