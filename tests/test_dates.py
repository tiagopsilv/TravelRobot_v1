from datetime import date

import pytest

from travelrobot.config import ConfigError, SearchRule
from travelrobot.dates import build_windows

TODAY = date(2027, 1, 1)


def rule(**overrides):
    values = {
        "city_name": "X",
        "text_for_search": "X",
        "reference_point": "Y",
        "start_date": date(2027, 3, 1),
        "end_date": date(2027, 3, 3),
    }
    return SearchRule(**(values | overrides))


def stays(**overrides):
    return [(w.check_in, w.check_out) for w in build_windows([rule(**overrides)], TODAY)]


def test_single_stay():
    assert stays() == [(date(2027, 3, 1), date(2027, 3, 3))]


def test_disabled_rule_is_skipped():
    assert stays(enabled=False) == []


def test_weekly_stays_end_on_sunday_and_respect_end_date():
    # 01/03/2027 é segunda-feira e 10/03/2027, quarta-feira.
    assert stays(range_type="weekly", end_date=date(2027, 3, 10)) == [
        (date(2027, 3, 1), date(2027, 3, 7)),
        (date(2027, 3, 8), date(2027, 3, 10)),
    ]


def test_weekly_starting_on_sunday_has_no_zero_night_stay():
    # 07/03/2027 é domingo.
    result = stays(range_type="weekly", start_date=date(2027, 3, 7), end_date=date(2027, 3, 20))
    assert result[0] == (date(2027, 3, 7), date(2027, 3, 14))
    assert all(check_out > check_in for check_in, check_out in result)


def test_today_and_end_of_month():
    assert stays(start_date="today", end_date="end_of_month") == [(TODAY, date(2027, 1, 31))]


def test_end_of_year():
    assert stays(end_date="end_of_year") == [(date(2027, 3, 1), date(2027, 12, 31))]


@pytest.mark.parametrize(
    "overrides",
    [
        {"end_date": date(2027, 3, 1)},
        {"start_date": date(2026, 12, 1), "end_date": date(2026, 12, 5)},
    ],
)
def test_invalid_dates_are_rejected(overrides):
    with pytest.raises(ConfigError):
        stays(**overrides)
