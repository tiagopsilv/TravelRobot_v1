from __future__ import annotations

import calendar
from datetime import date, timedelta

from travelrobot.config import ConfigError, SearchRule
from travelrobot.models import SearchWindow


def _resolve_start(rule: SearchRule, today: date) -> date:
    return today if rule.start_date == "today" else rule.start_date


def _resolve_end(rule: SearchRule, start: date) -> date:
    if rule.end_date == "end_of_year":
        return date(start.year, 12, 31)
    if rule.end_date == "end_of_month":
        return date(start.year, start.month, calendar.monthrange(start.year, start.month)[1])
    return rule.end_date


def _next_sunday_after(day: date) -> date:
    """Próximo domingo estritamente depois de `day`, para nunca gerar estadia de zero noites."""
    return day + timedelta(days=(6 - day.weekday()) or 7)


def _stays(rule: SearchRule, start: date, end: date) -> list[tuple[date, date]]:
    if rule.range_type == "single":
        return [(start, end)]

    stays = []
    check_in = start
    while check_in < end:
        check_out = min(_next_sunday_after(check_in), end)
        stays.append((check_in, check_out))
        check_in = check_out + timedelta(days=1)
    return stays


def build_windows(rules: list[SearchRule], today: date) -> list[SearchWindow]:
    windows = []
    for rule in rules:
        if not rule.enabled:
            continue
        start = _resolve_start(rule, today)
        end = _resolve_end(rule, start)
        if end <= start:
            raise ConfigError(
                f"{rule.city_name}: end_date ({end}) precisa ser depois de start_date ({start})."
            )
        if start < today:
            raise ConfigError(f"{rule.city_name}: start_date ({start}) já passou.")
        windows.extend(
            SearchWindow(
                city_name=rule.city_name,
                city_code=rule.city_code,
                text_for_search=rule.text_for_search,
                reference_point=rule.reference_point,
                website_url=rule.website_url,
                check_in=check_in,
                check_out=check_out,
            )
            for check_in, check_out in _stays(rule, start, end)
        )
    return windows
