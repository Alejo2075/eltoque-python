"""Date-range validation and formatting (internal).

The upstream time zone is **not documented**, so values are never converted: only naive
``datetime`` objects are accepted and are sent exactly as written, truncated to whole seconds.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from eltoque.exceptions import ElToqueValidationError

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
MAX_WINDOW = timedelta(hours=24)


def _check_naive(name: str, value: object) -> datetime:
    if not isinstance(value, datetime):
        raise ElToqueValidationError(f"{name} must be a datetime.datetime")
    if value.tzinfo is not None and value.utcoffset() is not None:
        raise ElToqueValidationError(
            f"{name} must be a naive datetime: the elTOQUE time zone is not documented, "
            "so no conversion is attempted. Drop tzinfo after normalizing it yourself."
        )
    return value.replace(microsecond=0, tzinfo=None)


def validate_range(date_from: datetime, date_to: datetime) -> tuple[str, str]:
    """Validate an explicit window and return the ``(date_from, date_to)`` query strings.

    Rules: both bounds naive, ``date_from < date_to`` and a window shorter than 24 hours
    (checked after truncating to whole seconds, i.e. on exactly what is sent).
    """
    start = _check_naive("date_from", date_from)
    end = _check_naive("date_to", date_to)
    if start >= end:
        raise ElToqueValidationError("date_from must be earlier than date_to")
    if end - start >= MAX_WINDOW:
        raise ElToqueValidationError(
            "the interval must be shorter than 24 hours (the API answers HTTP 400 otherwise)"
        )
    return start.strftime(DATE_FORMAT), end.strftime(DATE_FORMAT)
