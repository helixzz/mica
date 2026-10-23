"""Small date formatting helpers for user-facing text.

Business dates in this project are calendar dates (contract expiry, payment due).
Rendering them as raw ISO strings is fine in logs and APIs, but a card that says
``2026-10-30`` next to a Chinese label reads like a database dump. Two locales
are enough here because that is what Mica ships.
"""

from __future__ import annotations

from datetime import date, datetime

_MONTHS_EN = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)


def _coerce(value: date | datetime | str | None) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def fmt_date(
    value: date | datetime | str | None, locale: str = "zh-CN", *, empty: str = "—"
) -> str:
    day = _coerce(value)
    if day is None:
        return empty
    if locale.startswith("zh"):
        return f"{day.year}年{day.month}月{day.day}日"
    return f"{_MONTHS_EN[day.month - 1]} {day.day}, {day.year}"


def fmt_datetime(value: datetime | str | None, locale: str = "zh-CN", *, empty: str = "—") -> str:
    if value is None or value == "":
        return empty
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return empty
    day = fmt_date(value.date(), locale)
    return f"{day} {value.hour:02d}:{value.minute:02d}"
