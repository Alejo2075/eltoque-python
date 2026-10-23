import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from eltoque import ATTRIBUTION, ElToqueDecodeError, Rates
from eltoque.models import RateLimitInfo, RatesResponse


@pytest.mark.parametrize(
    "payload",
    [{"a": 1}, [1, 2, 3], "text", 42, 1.5, True, None, {"nested": {"x": [None]}}],
)
def test_data_is_preserved_as_is(payload: object) -> None:
    response = RatesResponse(data=payload)
    assert response.data == payload
    assert response.data is payload


def test_metadata_defaults() -> None:
    response = RatesResponse(data={})
    assert response.status_code == 200
    assert response.rate_limit == RateLimitInfo()
    assert response.received_at.tzinfo is UTC
    assert abs((datetime.now(UTC) - response.received_at).total_seconds()) < 5


def test_response_is_immutable() -> None:
    response = RatesResponse(data=1)
    with pytest.raises(AttributeError):
        response.data = 2  # type: ignore[misc]


# --- typed Rates view (synthetic fixture mimicking the shape confirmed on 2026-10-23) ---

FIXTURE = Path(__file__).parent / "fixtures" / "rates_synthetic.json"


def sample() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_typed_rates_from_synthetic_payload() -> None:
    rates = RatesResponse(data=sample()).rates
    assert rates.rates["AAA"] == Decimal("100.5")
    assert rates.rates["BBB"] == Decimal("250.25")
    assert rates.rates["CCC"] == Decimal(3)
    assert rates.rates["USDT_TRC20"] == Decimal("99.9")
    assert rates.reported_at == datetime(2026, 1, 15, 9, 5, 7)
    assert rates.reported_at.tzinfo is None  # zone undocumented: never assumed


def test_decimals_have_no_float_noise() -> None:
    payload = sample()
    payload["tasas"] = {"X": 0.1, "Y": 365.55, "Z": 1e-07}
    rates = Rates.from_payload(payload).rates
    assert str(rates["X"]) == "0.1"
    assert str(rates["Y"]) == "365.55"
    assert rates["Z"] == Decimal("1e-07")


def test_rates_mapping_is_read_only_and_open_ended() -> None:
    rates = Rates.from_payload(sample())
    with pytest.raises(TypeError):
        rates.rates["NEW"] = Decimal(1)  # type: ignore[index]
    assert "ZZZ" not in rates.rates  # codes are open: callers must look up defensively


def test_unknown_extra_keys_are_ignored_and_raw_data_is_untouched() -> None:
    payload = {**sample(), "extra": {"k": [1, 2]}}
    response = RatesResponse(data=payload)
    assert response.rates.rates["AAA"] == Decimal("100.5")
    assert response.data["extra"] == {"k": [1, 2]}


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: p.pop("tasas"),
        lambda p: p.update(tasas={}),
        lambda p: p.update(tasas=[1, 2]),
        lambda p: p.update(tasas={"A": "1.5"}),
        lambda p: p.update(tasas={"A": None}),
        lambda p: p.update(tasas={"A": True}),
        lambda p: p.update(tasas={"A": float("nan")}),
        lambda p: p.update(tasas={"A": float("inf")}),
        lambda p: p.pop("date"),
        lambda p: p.update(date="not-a-date"),
        lambda p: p.update(date=20260115),
        lambda p: p.pop("hour"),
        lambda p: p.update(hour="9"),
        lambda p: p.update(hour=True),
        lambda p: p.update(hour=24),
        lambda p: p.update(minutes=60),
        lambda p: p.update(seconds=-1),
    ],
)
def test_unexpected_shapes_raise_decode_error(mutate) -> None:  # type: ignore[no-untyped-def]
    payload = sample()
    mutate(payload)
    with pytest.raises(ElToqueDecodeError):
        Rates.from_payload(payload)


@pytest.mark.parametrize("payload", [None, [], "text", 5, [{"tasas": {}}]])
def test_non_object_payloads_raise_decode_error(payload: object) -> None:
    with pytest.raises(ElToqueDecodeError):
        _ = RatesResponse(data=payload).rates


def test_attribution_text() -> None:
    assert "elTOQUE" in ATTRIBUTION
    assert "not official" in ATTRIBUTION
