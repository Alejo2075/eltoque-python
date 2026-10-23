from datetime import UTC, date, datetime, timedelta, timezone

import pytest

from eltoque._dates import day_range, validate_range
from eltoque.exceptions import ElToqueValidationError

START = datetime(2022, 10, 27, 0, 0, 0)


def test_formats_exactly_as_documented() -> None:
    result = validate_range(START, datetime(2022, 10, 27, 23, 59, 59))
    assert result == ("2022-10-27 00:00:00", "2022-10-27 23:59:59")


def test_microseconds_are_truncated() -> None:
    result = validate_range(START.replace(microsecond=999999), START + timedelta(hours=1))
    assert result[0] == "2022-10-27 00:00:00"


def test_window_just_under_24h_is_accepted() -> None:
    validate_range(START, START + timedelta(hours=24) - timedelta(seconds=1))


@pytest.mark.parametrize("delta", [timedelta(hours=24), timedelta(days=3)])
def test_window_of_24h_or_more_rejected(delta: timedelta) -> None:
    with pytest.raises(ElToqueValidationError, match="24 hours"):
        validate_range(START, START + delta)


def test_validation_uses_truncated_values() -> None:
    # 23:59:59.9 truncates to 23:59:59, window stays below 24h.
    validate_range(START, START + timedelta(hours=23, minutes=59, seconds=59, microseconds=900000))


@pytest.mark.parametrize("offset", [timedelta(0), timedelta(seconds=-1)])
def test_equal_or_reversed_rejected(offset: timedelta) -> None:
    with pytest.raises(ElToqueValidationError, match="earlier"):
        validate_range(START, START + offset)


def test_sub_second_difference_collapses_and_is_rejected() -> None:
    with pytest.raises(ElToqueValidationError, match="earlier"):
        validate_range(START, START + timedelta(milliseconds=500))


@pytest.mark.parametrize("tz", [UTC, timezone(timedelta(hours=-5))])
def test_aware_datetimes_rejected(tz: timezone) -> None:
    with pytest.raises(ElToqueValidationError, match="naive"):
        validate_range(START.replace(tzinfo=tz), START + timedelta(hours=1))
    with pytest.raises(ElToqueValidationError, match="naive"):
        validate_range(START, (START + timedelta(hours=1)).replace(tzinfo=tz))


@pytest.mark.parametrize("bad", [None, "2022-10-27 00:00:00", 1666828800, START.date()])
def test_non_datetime_rejected(bad: object) -> None:
    with pytest.raises(ElToqueValidationError, match="datetime"):
        validate_range(bad, START)  # type: ignore[arg-type]
    with pytest.raises(ElToqueValidationError, match="datetime"):
        validate_range(START, bad)  # type: ignore[arg-type]


def test_day_range_covers_whole_day() -> None:
    start, end = day_range(date(2022, 10, 27))
    assert start == datetime(2022, 10, 27, 0, 0, 0)
    assert end == datetime(2022, 10, 27, 23, 59, 59)
    validate_range(start, end)  # always a legal window


@pytest.mark.parametrize("bad", [datetime(2022, 10, 27, 5), "2022-10-27", None])
def test_day_range_rejects_non_dates(bad: object) -> None:
    with pytest.raises(ElToqueValidationError, match="date"):
        day_range(bad)  # type: ignore[arg-type]
