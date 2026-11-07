"""Conversões de texto exibido em sites pt-BR para valores tipados."""
from __future__ import annotations

import re
from decimal import Decimal

_NUMBER = re.compile(r"\d[\d.,]*")
_DISTANCE = re.compile(
    r"(?P<number>\d[\d.,]*)\s*"
    r"(?P<unit>quil[oô]metros?|km|milhas?|mi|metros?|m|p[eé]s|ft)\b",
    re.IGNORECASE,
)
_KM_PER_UNIT = {
    "q": Decimal(1),
    "k": Decimal(1),
    "mi": Decimal("1.609344"),
    "me": Decimal("0.001"),
    "m": Decimal("0.001"),
    "p": Decimal("0.0003048"),
    "f": Decimal("0.0003048"),
}


def _to_decimal(raw: str) -> Decimal:
    number = raw.rstrip(".,")
    if "," in number and "." in number:
        decimal_mark = "," if number.rfind(",") > number.rfind(".") else "."
        thousands_mark = "." if decimal_mark == "," else ","
        number = number.replace(thousands_mark, "").replace(decimal_mark, ".")
    elif number.count(",") == 1:
        number = number.replace(",", ".")
    elif "," in number:
        number = number.replace(",", "")
    elif number.count(".") > 1 or re.fullmatch(r"\d{1,3}\.\d{3}", number):
        number = number.replace(".", "")
    return Decimal(number)


def parse_decimal(text: str | None) -> Decimal | None:
    """Extrai o primeiro número: "R$ 1.234,56" vira 1234.56, e "1.234" vira 1234."""
    match = _NUMBER.search(text or "")
    return _to_decimal(match.group()) if match else None


def parse_currency(text: str | None) -> str | None:
    """Identifica a moeda exibida: os sites podem mostrar US$ mesmo em páginas em português."""
    upper = (text or "").upper()
    for symbol, code in (("R$", "BRL"), ("US$", "USD"), ("€", "EUR"), ("£", "GBP")):
        if symbol in upper:
            return code
    match = re.search(r"\b(BRL|USD|EUR|GBP)\b", upper)
    return match.group(1) if match else None


def parse_int(text: str | None) -> int | None:
    """Extrai um inteiro, ignorando separadores de milhar: "1.234 avaliações" vira 1234."""
    match = _NUMBER.search(text or "")
    return int(re.sub(r"\D", "", match.group())) if match else None


def parse_distance_km(text: str | None) -> Decimal | None:
    """Converte "3,2 km", "800 m", "2,1 milhas" ou "500 pés" para km. Sem unidade: None."""
    match = _DISTANCE.search(text or "")
    if not match:
        return None
    unit = match["unit"].casefold()
    key = unit[:2] if unit[:2] in _KM_PER_UNIT else unit[0]
    return (_to_decimal(match["number"]) * _KM_PER_UNIT[key]).quantize(Decimal("0.001"))


def normalize_name(name: str) -> str:
    """Chave para comparar hotéis entre fontes, ignorando caixa e espaços extras."""
    return " ".join(name.split()).casefold()


def extract_external_link(href: str | None) -> str | None:
    """Links do Google embutem o destino: "/aclk?adurl=https://hotel.com" vira "https://hotel.com"."""
    if not href:
        return None
    match = re.search(r"https?://", href)
    return href[match.start() :] if match else None
