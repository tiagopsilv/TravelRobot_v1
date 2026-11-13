from __future__ import annotations

import csv
import hashlib
import io
import os
import re
import unicodedata
from collections import Counter, defaultdict
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
# Colunas do CSV de cada fonte: só as que ela preenche, numa ordem fixa para a planilha não mudar
# de um dia para o outro. As chaves são os nomes das fontes (SOURCE de cada módulo).
SOURCE_COLUMNS = {
    "Smiles": [
        "data_execucao", "tipo", "categoria", "titulo", "descricao", "beneficio", "valor", "unidade",
        "exclusivo_clube", "inicio", "hora_inicio", "fim", "hora_fim", "duracao_dias", "dias_restantes",
        "cupom", "link",
    ],
    "Livelo": [
        "data_execucao", "parceiro", "tipo", "categoria", "titulo", "descricao", "beneficio", "valor",
        "unidade", "valor_clube", "valor_normal", "multiplicador", "exclusivo_clube", "inicio",
        "hora_inicio", "fim", "hora_fim", "duracao_dias", "dias_restantes", "cupom", "regras", "link",
    ],
    "Esfera": [
        "data_execucao", "parceiro", "titulo", "beneficio", "valor", "unidade", "valor_clube", "inicio",
        "hora_inicio", "fim", "hora_fim", "duracao_dias", "dias_restantes", "prazo_credito_dias", "cupom",
        "regras", "link",
    ],
    "Pontos pra Voar (Radar PPV)": [
        "data_execucao", "programa", "parceiro", "tipo", "beneficio", "valor", "unidade", "descricao",
        "publicado_em", "fim", "hora_fim", "dias_restantes", "link",
    ],
}  # fmt: skip
# Os blogs têm o nome que está em selectors.toml; todos usam as colunas de notícia.
FEED_COLUMNS = [
    "data_execucao", "programa", "tipo", "categoria", "titulo", "beneficio", "valor", "unidade",
    "valor_clube", "exclusivo_clube", "publicado_em", "fim", "dias_restantes", "cupom", "link",
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


def save_promotions(promotions: list[Promotion], directory: Path, run_date: date) -> list[Path]:
    """Grava o CSV com todas as fontes e um CSV por fonte, só com as colunas que ela preenche."""
    stamp = f"{run_date:%Y%m%d}"
    rows = [dict(zip(PROMOTION_COLUMNS, _promotion_row(p))) for p in promotions]
    path = directory / f"FrequentFlyersList_{stamp}.csv"
    _write_csv(path, PROMOTION_COLUMNS, [list(row.values()) for row in rows])
    paths = [path]

    by_source: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_source[str(row["fonte"])].append(row)
    names = _file_names(list(by_source))
    for source, source_rows in by_source.items():
        columns = SOURCE_COLUMNS.get(source, FEED_COLUMNS)
        source_path = directory / "Promocoes" / f"FrequentFlyersList_{names[source]}_{stamp}.csv"
        _write_csv(source_path, columns, [[row[column] for column in columns] for row in source_rows])
        paths.append(source_path)
    return paths


def _file_names(sources: list[str]) -> dict[str, str]:
    """Um nome de arquivo por fonte, sem repetir.

    Fontes que viram o mesmo nome ("Blog A" e "Blog Á", ou só caixa diferente, que o Windows não
    distingue) ganham um sufixo tirado do nome original, para uma não sobrescrever a outra.
    """
    names = {source: _file_name(source) for source in sources}
    taken = Counter(name.casefold() for name in names.values())
    return {
        source: f"{name}_{hashlib.sha1(source.encode()).hexdigest()[:6]}" if taken[name.casefold()] > 1 else name
        for source, name in names.items()
    }


def _file_name(source: str) -> str:
    """"Pontos pra Voar (Radar PPV)" vira "PontosPraVoarRadarPPV"; "Melhores Cartões", "MelhoresCartoes"."""
    plain = unicodedata.normalize("NFKD", source).encode("ascii", "ignore").decode()
    return "".join(word[:1].upper() + word[1:] for word in re.findall(r"[A-Za-z0-9]+", plain)) or "Fonte"
