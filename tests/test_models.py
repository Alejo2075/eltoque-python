from datetime import UTC, datetime

import pytest

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
