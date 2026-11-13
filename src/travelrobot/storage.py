from __future__ import annotations

import csv
import io
import os
import re
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
    "data_execucao", "fonte", "programa", "parceiro", "tipo", "categoria", "titulo", "descricao",
    "beneficio", "valor", "unidade", "valor_clube", "valor_normal", "multiplicador", "exclusivo_clube",
    "publicado_em", "inicio", "hora_inicio", "fim", "hora_fim", "duracao_dias", "dias_restantes",
    "prazo_credito_dias", "cupom", "regras", "link",
]  # fmt: skip
# "Utilize o cupom LIVELO" ou "cupom: BLACK10": o código vem em maiúsculas logo depois de "cupom".
_COUPON = re.compile(r"(?i:cupom)\s*:?\s*([A-Z0-9][A-Z0-9_-]{2,})\b")
# Só o que dispensa o cupom logo antes dele: "não é necessário cupom", "dispensa o uso de cupom".
# "Não perca: use o cupom X" e "sem cupom X não pontua" pedem o código e não entram aqui.
_COUPON_NOT_NEEDED = re.compile(
    r"(?:n[aã]o\s+(?:[eé]\s+)?(?:necess[aá]ri\w*|precis\w*)|(?P<waiver>\bdispens(?:a|ado|ada|ados|adas|[aá]vel|[aá]veis)\b)|sem\s+necessidade)"
    r"(?:\s+(?:de|do|usar|utilizar|uso|o|um|nenhum))*\s*$",
    re.IGNORECASE,
)
# "não dispensa", "não é dispensado", "não será dispensado": a dispensa negada exige o código.
_WAIVER_NEGATED = re.compile(r"n[aã]o\s+(?:\w+\s+)?$", re.IGNORECASE)


def _coupon_not_needed(before: str) -> bool:
    match = _COUPON_NOT_NEEDED.search(before)
    return bool(match) and not (match["waiver"] and _WAIVER_NEGATED.search(before[: match.start()]))
# Palavras que aparecem em maiúsculas depois de "cupom" sem serem o código.
_NOT_A_COUPON = {
    "DE", "DO", "DA", "E", "O", "A", "NO", "NA", "PARA", "COM", "DESCONTO", "PROMOCIONAL", "VALIDO",
    "VÁLIDO", "NECESSARIO", "NECESSÁRIO", "EXCLUSIVO", "OFF",
}  # fmt: skip


def _coupon(*texts: str) -> str:
    """O primeiro código de cupom citado, ignorando "não é necessário cupom" e palavras comuns."""
    for text in texts:
        for match in _COUPON.finditer(text):
            code = match[1]
            if code in _NOT_A_COUPON or _coupon_not_needed(text[: match.start()]):
                continue
            return code
    return ""


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


def _promotion_row(p: Promotion) -> list[object]:
    """Os campos da fonte e os derivados: ganho sobre o normal, duração, dias até acabar e cupom."""
    executed = p.executed_at.date()
    multiplier = (p.value / p.regular_value).quantize(Decimal("0.01")) if p.value and p.regular_value else None
    return [
        executed.isoformat(), p.source, p.program, p.partner, p.kind, p.category, p.title,
        p.description, p.benefit, p.value, p.unit, p.club_value, p.regular_value, multiplier,
        {True: "sim", False: "não"}.get(p.club_only, ""), p.published and p.published.isoformat(),
        p.start and p.start.isoformat(), p.start_time, p.end and p.end.isoformat(), p.end_time,
        (p.end - p.start).days + 1 if p.start and p.end else None,
        (p.end - executed).days if p.end else None,
        p.credit_days, _coupon(p.rules, p.description, p.title), p.rules, p.link,
    ]  # fmt: skip


def save_promotions(promotions: list[Promotion], directory: Path, run_date: date) -> Path:
    path = directory / f"FrequentFlyersList_{run_date:%Y%m%d}.csv"
    _write_csv(path, PROMOTION_COLUMNS, [_promotion_row(p) for p in promotions])
    return path
