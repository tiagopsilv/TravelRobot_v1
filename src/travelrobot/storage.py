from __future__ import annotations

import csv
import io
import os
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

from travelrobot.models import GuestReviews, HotelOffer, Promotion

LIST_SEPARATOR = " | "
HOTEL_COLUMNS = [
    "data_execucao", "site", "check_in", "check_out", "cidade", "hotel", "preco", "moeda", "nota",
    "condicoes_pagamento", "noites", "pessoas", "endereco", "distancia_km", "avaliacao_nota",
    "avaliacao_quantidade", "temas_positivos", "temas_negativos", "notas_outros_sites", "link",
]  # fmt: skip
PROMOTION_COLUMNS = [
    "data_execucao", "fonte", "programa", "parceiro", "tipo", "titulo", "descricao", "beneficio",
    "valor", "inicio", "fim", "link",
]  # fmt: skip


def _cell(value: object) -> object:
    """Decimais com vírgula, para o Excel em pt-BR reconhecer os números."""
    if isinstance(value, Decimal):
        return str(value).replace(".", ",")
    return "" if value is None else value


def _write_atomic(path: Path, content: str, encoding: str) -> None:
    """Grava num temporário e troca no fim: uma falha nunca deixa um arquivo pela metade."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(content, encoding=encoding, newline="")
    os.replace(temporary, path)


def _write_csv(path: Path, columns: list[str], rows: list[list[object]]) -> None:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(columns)
    writer.writerows([_cell(value) for value in row] for row in rows)
    _write_atomic(path, buffer.getvalue(), "utf-8-sig")


def _hotel_row(offer: HotelOffer) -> list[object]:
    reviews = offer.reviews or GuestReviews()
    return [
        offer.executed_at.date().isoformat(), offer.source, offer.check_in.isoformat(),
        offer.check_out.isoformat(), offer.city_name, offer.hotel_name, offer.price, offer.currency,
        offer.rating,
        offer.payment_conditions, offer.nights, offer.people, offer.address, offer.distance_km,
        reviews.rating, reviews.review_count, LIST_SEPARATOR.join(reviews.positive_topics),
        LIST_SEPARATOR.join(reviews.negative_topics), LIST_SEPARATOR.join(reviews.other_sites),
        offer.link,
    ]  # fmt: skip


def save_hotels(offers: list[HotelOffer], directory: Path, run_date: date) -> list[Path]:
    """Grava um CSV e um HTML por cidade."""
    by_city: dict[str, list[HotelOffer]] = defaultdict(list)
    for offer in offers:
        by_city[offer.city_name].append(offer)

    paths = []
    stamp = f"{run_date:%Y%m%d}"
    for city, city_offers in by_city.items():
        csv_path = directory / f"HotelsList_{city}_{stamp}.csv"
        _write_csv(csv_path, HOTEL_COLUMNS, [_hotel_row(offer) for offer in city_offers])
        html_path = directory / "Htmls" / f"HtmlHotel_{city}_{stamp}.html"
        body = "\n".join(offer.html for offer in city_offers)
        _write_atomic(html_path, f"<h1>DATA: {stamp}</h1>\n{body}\n", "utf-8")
        paths += [csv_path, html_path]
    return paths


def save_promotions(promotions: list[Promotion], directory: Path, run_date: date) -> Path:
    path = directory / f"FrequentFlyersList_{run_date:%Y%m%d}.csv"
    rows = [
        [
            p.executed_at.date().isoformat(), p.source, p.program, p.partner, p.kind, p.title,
            p.description, p.benefit, p.value, p.start and p.start.isoformat(),
            p.end and p.end.isoformat(), p.link,
        ]
        for p in promotions
    ]  # fmt: skip
    _write_csv(path, PROMOTION_COLUMNS, rows)
    return path
