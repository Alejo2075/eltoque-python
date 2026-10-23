import asyncio
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


async def test_async_context_manager_closes_client() -> None:
    recorder = Recorder(json_response())
    async with make(recorder) as client:
        await client.get_latest_rates()
    with pytest.raises(exc.ElToqueError, match="closed"):
        await client.get_latest_rates()
    assert len(recorder.requests) == 1


async def test_aclose_is_idempotent_and_closes_owned_client() -> None:
    client = make(Recorder(json_response()))
    await client.aclose()
    await client.aclose()
    assert client._http.is_closed


async def test_cannot_reenter_closed_client() -> None:
    client = make(Recorder(json_response()))
    await client.aclose()
    with pytest.raises(exc.ElToqueError, match="closed"):
        async with client:
            pass


async def test_injected_client_is_used_and_not_closed() -> None:
    recorder = Recorder(json_response())
    http = httpx.AsyncClient(transport=httpx.MockTransport(recorder))
    async with AsyncElToqueClient(TOKEN, http_client=http) as client:
        await client.get_latest_rates()
    assert len(recorder.requests) == 1
    assert not http.is_closed
    await http.aclose()


async def test_injected_client_cannot_make_sdk_follow_redirects() -> None:
    recorder = Recorder(httpx.Response(307, headers={"Location": "https://evil.test/"}))
    http = httpx.AsyncClient(transport=httpx.MockTransport(recorder), follow_redirects=True)
    with pytest.raises(exc.ElToqueAPIError):
        await AsyncElToqueClient(TOKEN, http_client=http).get_latest_rates()
    assert len(recorder.requests) == 1
    await http.aclose()


async def test_http_client_and_transport_are_mutually_exclusive() -> None:
    http = httpx.AsyncClient()
    with pytest.raises(exc.ElToqueConfigurationError):
        AsyncElToqueClient(TOKEN, http_client=http, transport=httpx.MockTransport(Recorder()))
    await http.aclose()


@pytest.fixture
def sleeps(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    calls: list[float] = []

    async def fake_sleep(delay: float) -> None:
        calls.append(delay)

    monkeypatch.setattr("eltoque._async_client.asyncio.sleep", fake_sleep)
    return calls


async def test_no_retries_by_default(sleeps: list[float]) -> None:
    recorder = Recorder(httpx.Response(429, headers={"Retry-After": "1"}))
    with pytest.raises(exc.ElToqueRateLimitError):
        await make(recorder).get_latest_rates()
    assert len(recorder.requests) == 1
    assert sleeps == []


async def test_retry_after_is_honored_then_succeeds(sleeps: list[float]) -> None:
    recorder = Recorder(httpx.Response(429, headers={"Retry-After": "3"}), json_response([1]))
    response = await make(recorder, max_retries=2).get_latest_rates()
    assert response.data == [1]
    assert sleeps == [3.0]


async def test_retries_are_bounded(sleeps: list[float]) -> None:
    recorder = Recorder(httpx.Response(503))
    with pytest.raises(exc.ElToqueServerError):
        await make(recorder, max_retries=2).get_latest_rates()
    assert len(recorder.requests) == 3
    assert sleeps == [0.5, 1.0]


@pytest.mark.parametrize("status", [400, 401, 422])
async def test_client_errors_are_never_retried(status: int, sleeps: list[float]) -> None:
    recorder = Recorder(httpx.Response(status))
    with pytest.raises(exc.ElToqueAPIError):
        await make(recorder, max_retries=3).get_latest_rates()
    assert len(recorder.requests) == 1
    assert sleeps == []


async def test_cancellation_during_backoff_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    async def cancelled(delay: float) -> None:
        raise asyncio.CancelledError

    monkeypatch.setattr("eltoque._async_client.asyncio.sleep", cancelled)
    recorder = Recorder(httpx.Response(503))
    with pytest.raises(asyncio.CancelledError):
        await make(recorder, max_retries=3).get_latest_rates()
    assert len(recorder.requests) == 1


async def test_real_sleep_is_non_blocking() -> None:
    recorder = Recorder(httpx.Response(429, headers={"Retry-After": "0"}), json_response())
    response = await make(recorder, max_retries=1).get_latest_rates()
    assert response.status_code == 200
