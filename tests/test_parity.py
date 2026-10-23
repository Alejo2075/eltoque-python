"""The same scenario must behave identically for the sync and async clients."""

from __future__ import annotations

import inspect
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

import httpx
import pytest

import eltoque
from eltoque import exceptions as exc
from tests.conftest import TOKEN, Recorder, json_response

if TYPE_CHECKING:
    from collections.abc import Callable


async def call(kind: str, recorder: Recorder, method: str, *args: Any, **kwargs: Any) -> Any:
    transport = httpx.MockTransport(recorder)
    if kind == "sync":
        with eltoque.ElToqueClient(TOKEN, transport=transport, **kwargs) as client:
            return getattr(client, method)(*args)
    async with eltoque.AsyncElToqueClient(TOKEN, transport=transport, **kwargs) as aclient:
        return await getattr(aclient, method)(*args)


@pytest.fixture(params=["sync", "async"])
def kind(request: pytest.FixtureRequest) -> str:
    return str(request.param)


async def test_same_request_on_the_wire(kind: str) -> None:
    recorder = Recorder(json_response([1]))
    await call(kind, recorder, "get_rates", datetime(2022, 10, 27), datetime(2022, 10, 27, 12))
    request = recorder.requests[0]
    assert request.url.path == "/v1/trmi"
    assert dict(request.url.params) == {
        "date_from": "2022-10-27 00:00:00",
        "date_to": "2022-10-27 12:00:00",
    }
    assert request.headers["authorization"] == f"Bearer {TOKEN}"


async def test_same_response_object(kind: str) -> None:
    recorder = Recorder(json_response({"k": "v"}, **{"X-RateLimit-Limit": "60"}))
    response = await call(kind, recorder, "get_latest_rates")
    assert response.data == {"k": "v"}
    assert response.status_code == 200
    assert response.rate_limit.limit == 60


@pytest.mark.parametrize(
    ("make_response", "expected"),
    [
        (lambda: httpx.Response(400), exc.ElToqueBadRequestError),
        (lambda: httpx.Response(401), exc.ElToqueAuthenticationError),
        (lambda: httpx.Response(422), exc.ElToqueUnprocessableError),
        (lambda: httpx.Response(429, headers={"Retry-After": "5"}), exc.ElToqueRateLimitError),
        (lambda: httpx.Response(502), exc.ElToqueServerError),
        (lambda: httpx.Response(418), exc.ElToqueAPIError),
        (lambda: httpx.Response(200, content=b"nope"), exc.ElToqueDecodeError),
        (lambda: httpx.ReadTimeout("t"), exc.ElToqueTimeoutError),
        (lambda: httpx.ConnectError("c"), exc.ElToqueNetworkError),
    ],
)
async def test_same_errors(
    kind: str, make_response: Callable[[], httpx.Response | Exception], expected: type
) -> None:
    with pytest.raises(expected) as info:
        await call(kind, Recorder(make_response()), "get_latest_rates")
    assert type(info.value) is expected


async def test_same_validation_errors(kind: str) -> None:
    recorder = Recorder(json_response())
    with pytest.raises(exc.ElToqueValidationError):
        await call(kind, recorder, "get_rates", datetime(2022, 1, 1), datetime(2022, 1, 3))
    with pytest.raises(exc.ElToqueValidationError):
        await call(kind, recorder, "get_rates_for_day", datetime(2022, 1, 1))
    assert recorder.requests == []


async def test_day_helper_equivalence(kind: str) -> None:
    recorder = Recorder(json_response())
    await call(kind, recorder, "get_rates_for_day", date(2022, 10, 27))
    assert recorder.requests[0].url.params["date_to"] == "2022-10-27 23:59:59"


def test_public_signatures_match() -> None:
    sync_sig = inspect.signature(eltoque.ElToqueClient.__init__)
    async_sig = inspect.signature(eltoque.AsyncElToqueClient.__init__)
    assert list(sync_sig.parameters) == list(async_sig.parameters)
    for name in ("get_latest_rates", "get_rates", "get_rates_for_day"):
        s = inspect.signature(getattr(eltoque.ElToqueClient, name))
        a = inspect.signature(getattr(eltoque.AsyncElToqueClient, name))
        assert list(s.parameters) == list(a.parameters), name
        assert inspect.iscoroutinefunction(getattr(eltoque.AsyncElToqueClient, name))
