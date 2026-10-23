import json
from datetime import date, datetime

import httpx
import pytest

from eltoque import exceptions as exc
from eltoque._async_client import AsyncElToqueClient
from tests.conftest import TOKEN, Recorder, json_response


def make(recorder: Recorder, **kwargs: object) -> AsyncElToqueClient:
    return AsyncElToqueClient(TOKEN, transport=httpx.MockTransport(recorder), **kwargs)  # type: ignore[arg-type]


async def test_latest_rates_request_shape() -> None:
    recorder = Recorder(json_response({"any": "shape"}))
    response = await make(recorder).get_latest_rates()
    request = recorder.requests[0]
    assert str(request.url) == "https://tasas.eltoque.com/v1/trmi"
    assert request.headers["Authorization"] == f"Bearer {TOKEN}"
    assert response.data == {"any": "shape"}


async def test_ranged_rates_and_day() -> None:
    recorder = Recorder(json_response([1]))
    client = make(recorder)
    await client.get_rates(datetime(2022, 10, 27), datetime(2022, 10, 27, 23, 59, 59))
    await client.get_rates_for_day(date(2022, 10, 27))
    for request in recorder.requests:
        assert request.url.params["date_from"] == "2022-10-27 00:00:00"
        assert request.url.params["date_to"] == "2022-10-27 23:59:59"


async def test_invalid_range_fails_before_any_request() -> None:
    recorder = Recorder(json_response())
    with pytest.raises(exc.ElToqueValidationError):
        await make(recorder).get_rates(datetime(2022, 10, 27), datetime(2022, 10, 28))
    assert recorder.requests == []


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (400, exc.ElToqueBadRequestError),
        (401, exc.ElToqueAuthenticationError),
        (422, exc.ElToqueUnprocessableError),
        (429, exc.ElToqueRateLimitError),
        (500, exc.ElToqueServerError),
        (404, exc.ElToqueAPIError),
    ],
)
async def test_error_statuses_raise(status: int, expected: type[exc.ElToqueAPIError]) -> None:
    with pytest.raises(expected):
        await make(Recorder(httpx.Response(status))).get_latest_rates()


@pytest.mark.parametrize("payload", [None, 0, "x", [], {}])
async def test_any_json_value_is_returned_untouched(payload: object) -> None:
    recorder = Recorder(httpx.Response(200, content=json.dumps(payload)))
    assert (await make(recorder).get_latest_rates()).data == payload


async def test_invalid_body_raises_decode_error() -> None:
    with pytest.raises(exc.ElToqueDecodeError):
        await make(Recorder(httpx.Response(200, content=b"<html>"))).get_latest_rates()


async def test_transport_failures_are_translated() -> None:
    with pytest.raises(exc.ElToqueTimeoutError):
        await make(Recorder(httpx.ReadTimeout("slow"))).get_latest_rates()
    with pytest.raises(exc.ElToqueNetworkError):
        await make(Recorder(httpx.ConnectError("down"))).get_latest_rates()


async def test_redirect_is_not_followed() -> None:
    recorder = Recorder(httpx.Response(302, headers={"Location": "https://evil.test/"}))
    with pytest.raises(exc.ElToqueAPIError):
        await make(recorder).get_latest_rates()
    assert len(recorder.requests) == 1


def test_repr_has_no_token() -> None:
    assert TOKEN not in repr(make(Recorder(json_response())))
