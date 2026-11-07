from decimal import Decimal

import pytest

from travelrobot.parsing import (
    extract_external_link,
    normalize_name,
    parse_currency,
    parse_decimal,
    parse_distance_km,
    parse_int,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("R$ 1.234,56", "1234.56"),
        ("R$ 1.234", "1234"),
        ("1.234.567", "1234567"),
        ("4,5 de 5", "4.5"),
        ("4.5", "4.5"),
        ("1,234.56", "1234.56"),
        ("Nota 9", "9"),
    ],
)
def test_parse_decimal(text, expected):
    assert parse_decimal(text) == Decimal(expected)


@pytest.mark.parametrize("text", [None, "", "sem número"])
def test_parse_decimal_without_number(text):
    assert parse_decimal(text) is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [("R$ 900", "BRL"), ("US$ 129", "USD"), ("€ 80", "EUR"), ("129", None), (None, None)],
)
def test_parse_currency(text, expected):
    assert parse_currency(text) == expected


def test_parse_int_ignores_thousands_separator():
    assert parse_int("· 1.234 avaliações") == 1234


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3,2 km", "3.200"),
        ("1.234 km", "1234.000"),
        ("800 m", "0.800"),
        ("1 milha", "1.609"),
        ("2,1 milhas", "3.380"),
        ("500 pés", "0.152"),
        ("12 quilômetros", "12.000"),
    ],
)
def test_parse_distance_km(text, expected):
    assert parse_distance_km(text) == Decimal(expected)


@pytest.mark.parametrize("text", [None, "", "32", "sem rota"])
def test_parse_distance_without_unit_is_not_zero(text):
    assert parse_distance_km(text) is None


def test_normalize_name():
    assert normalize_name("  Hotel   PLAZA ") == "hotel plaza"


@pytest.mark.parametrize(
    ("href", "expected"),
    [
        ("/aclk?x=1&adurl=https://hotel.com/a", "https://hotel.com/a"),
        ("/aclk?adurl=http://hotel.com", "http://hotel.com"),
        ("/sem-destino", None),
        (None, None),
    ],
)
def test_extract_external_link(href, expected):
    assert extract_external_link(href) == expected
