"""Deduz tipo e benefício de uma promoção a partir de texto livre (títulos de notícias e cartões)."""
from __future__ import annotations

import re
from decimal import Decimal

from travelrobot.parsing import parse_decimal

_KINDS = [
    ("Transferência de pontos", re.compile(r"transf[ei]r|convert", re.IGNORECASE)),
    ("Acúmulo de pontos", re.compile(r"por\s+(?:real|d[oó]lar)", re.IGNORECASE)),
    ("Compra de pontos", re.compile(r"compra\s+de\s+(?:milhas|pontos|avios)|milheiro", re.IGNORECASE)),
    ("Clubes", re.compile(r"\bclube\b|assinatura", re.IGNORECASE)),
]
_BENEFIT = re.compile(
    r"(?:até\s+)?\d[\d.,]*\s*%\s+(?:de\s+)?(?:bônus|desconto|off)"
    r"|(?:até\s+)?\d[\d.,]*\s+(?:pontos|milhas)(?:\s+[\w&]+){0,3}?\s+por\s+(?:real|d[oó]lar)"
    r"|\d[\d.,]*\s*(?:mil\s+)?(?:pontos|milhas|avios)",
    re.IGNORECASE,
)


def infer_kind(text: str) -> str:
    return next((kind for kind, pattern in _KINDS if pattern.search(text)), "Notícia")


def extract_benefit(text: str) -> str:
    """O primeiro benefício citado: "até 120% de bônus", "11 pontos Livelo por real", "23.000 pontos"."""
    match = _BENEFIT.search(text)
    return " ".join(match.group().split()) if match else ""


def benefit_value(benefit: str) -> Decimal | None:
    """"até 120% de bônus" vira 120; "104 mil pontos" vira 104000."""
    value = parse_decimal(benefit)
    if value is not None and re.search(r"\bmil\s+(?:pontos|milhas|avios)", benefit, re.IGNORECASE):
        value *= 1000
    return value
