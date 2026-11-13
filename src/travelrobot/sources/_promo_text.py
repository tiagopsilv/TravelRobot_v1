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
_NUMBER = r"\d[\d.,]*"
_CURRENCY = r"reais|real|r\$|d[oó]lares|d[oó]lar|us\$|u\$"
# Benefícios reconhecidos, do mais específico ao mais genérico; vale o que aparece primeiro no texto.
_PERCENT = re.compile(rf"(?:até\s+)?({_NUMBER})\s*%\s+(?:de\s+)?(bônus|bonus|desconto|off)\b", re.IGNORECASE)
_RATE = re.compile(
    rf"(?:até\s+)?({_NUMBER})\s+(?:pontos|milhas)(?:\s+[\w&]+){{0,3}}?\s+(?:por|a\s+cada)\s+"
    rf"(?:({_NUMBER})\s+)?({_CURRENCY})(?:\s*({_NUMBER}))?(?!\w)",
    re.IGNORECASE,
)
_POINTS = re.compile(rf"({_NUMBER})\s*(mil\s+)?(?:pontos|milhas|avios)\b", re.IGNORECASE)
_CLUB_ONLY = re.compile(r"exclusiv\w*\s+(?:para\s+)?(?:os\s+)?(?:assinantes\s+)?(?:d[oa]\s+)?clube", re.IGNORECASE)
# Negações; "não perca", "sem perder" e o público "não assinantes" não negam benefício.
_NEGATION = re.compile(
    r"\b(?:n[aã]o|sem|nenhum\w*|nunca)\b(?![\s-]+(?:assinantes|perca|perder|deixe|fique))", re.IGNORECASE
)
_NOT_EXCLUSIVE = re.compile(r"n[aã]o\s+(?:[eé]\s+)?exclusiv", re.IGNORECASE)
_OTHERS = r"demais\s+clientes|clientes\s+em\s+geral|todos\s+os\s+clientes|n[aã]o[\s-]+assinantes"
# Um benefício dado também a quem não assina: "10 pontos por real (para os) demais clientes".
_OPEN_TO_OTHERS = re.compile(
    rf"(?:pontos|milhas|%|b[oô]nus|desconto)(?:\s+(?!n[aã]o\b)[\w$]+){{0,4}}?\s+(?:para\s+)?(?:os\s+)?(?:{_OTHERS})"
    r"(?!\s+n[aã]o\s)",
    re.IGNORECASE,
)


def infer_kind(text: str, default: str = "Notícia") -> str:
    return next((kind for kind, pattern in _KINDS if pattern.search(text)), default)


def parse_benefit(text: str) -> tuple[str, Decimal | None, str]:
    """O primeiro benefício citado: (trecho do texto, número, unidade do número).

    Taxas de acúmulo são normalizadas para 1 unidade da moeda: "3 pontos a cada 2 reais" vira 1,5
    pontos por R$. Assim só se comparam valores da mesma unidade.
    """
    found = [match for pattern in (_PERCENT, _RATE, _POINTS) if (match := pattern.search(text))]
    if not found:
        return "", None, ""
    match = min(found, key=lambda m: m.start())
    benefit = " ".join(match.group().split())
    value = parse_decimal(match[1])
    if match.re is _PERCENT:
        return benefit, value, "% de desconto" if match[2].lower() in ("desconto", "off") else "% de bônus"
    if match.re is _RATE:
        dollar = re.match(r"d|us|u\$", match[3], re.IGNORECASE)
        per = parse_decimal(match[2] or match[4] or "1")
        if value is not None and per:
            value = value / per
        return benefit, value, "pontos por US$" if dollar else "pontos por R$"
    if value is not None and match[2]:
        value *= 1000
    return benefit, value, "pontos"


def extract_benefit(text: str) -> str:
    """"até 120% de bônus", "11 pontos Livelo por real", "23.000 pontos"."""
    return parse_benefit(text)[0]


def benefit_value(benefit: str) -> Decimal | None:
    """"até 120% de bônus" vira 120; "104 mil pontos" vira 104000."""
    return parse_benefit(benefit)[1]


def value_unit(benefit: str) -> str:
    """A unidade de um benefício já isolado, inclusive os rótulos do Radar PPV ("Bonificação até 25%")."""
    if not re.search(r"\d", benefit):
        return ""
    text = benefit.lower()
    if "%" in text:
        if re.search(r"desconto|\boff\b", text):
            return "% de desconto"
        return "% de bônus" if re.search(r"b[oô]nus|bonifica", text) else "%"
    if re.search(r"d[oó]lar|us\$|u\$", text):
        return "pontos por US$"
    if re.search(r"por\s+(?:real|r\$)|a\s+cada\s+\d+\s+rea|pontua[cç][aã]o", text):
        return "pontos por R$"
    return "pontos"


def club_value(text: str) -> Decimal | None:
    """A taxa citada junto do clube: "11 pontos por real com Clube Livelo" vira 11."""
    for match in _RATE.finditer(text):
        after = text[match.end() : match.end() + 50]
        if re.match(r"\s*(?:gasto\s+)?(?:com|no|para|exclusiv\w*\s+para)\s+(?:o\s+)?(?:assinantes\s+)?(?:d[oa]\s+)?"
                    r"(?:clientes\s+)?clube", after, re.IGNORECASE):  # fmt: skip
            return parse_benefit(match.group())[1]
    return None


def club_only(text: str) -> bool | None:
    """Exclusiva do clube? None quando o texto não diz ou é ambíguo.

    - "não exclusiva", ou um benefício para "demais clientes" sem negação no texto: False.
    - Benefício para os demais e negação no mesmo texto ("sem bônus para demais clientes",
      "não oferece 10.000 pontos para demais clientes"): ambíguo para uma regra de texto, então None.
    - "Exclusiva do Clube", inclusive com "não válida para demais clientes": True.
    """
    if not re.search(r"clube", text, re.IGNORECASE):
        return None
    if _NOT_EXCLUSIVE.search(text):
        return False
    if _OPEN_TO_OTHERS.search(text):
        return None if _NEGATION.search(text) else False
    return True if _CLUB_ONLY.search(text) else None
