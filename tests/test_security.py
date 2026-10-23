"""The API token must never leak through errors, reprs, logs or tracebacks."""

from __future__ import annotations

import logging
import traceback
from typing import Any

import httpx
import pytest

import eltoque
from eltoque import exceptions as exc
from tests.conftest import TOKEN, Recorder, json_response

SECRET = "SECRET-TOKEN-VALUE.abc_123"

FAILURES = [
    lambda: httpx.Response(400, text=f"echo {SECRET}"),
    lambda: httpx.Response(401, text=f"bad token {SECRET}"),
    lambda: httpx.Response(422, json={"detail": SECRET}),
    lambda: httpx.Response(429, text=SECRET, headers={"Retry-After": "1"}),
    lambda: httpx.Response(500, text=f"<html>{SECRET}</html>"),
    lambda: httpx.Response(302, headers={"Location": f"https://evil.test/?t={SECRET}"}),
    lambda: httpx.Response(200, text=f"not json {SECRET}"),
    lambda: httpx.ConnectError(f"cannot connect with {SECRET}"),
    lambda: httpx.ReadTimeout(f"timeout {SECRET}"),
]


def everything_about(error: BaseException) -> str:
    parts = [str(error), repr(error), repr(vars(error))]
    parts.append("".join(traceback.format_exception(error)))
    return "\n".join(parts)


@pytest.mark.parametrize("make_failure", FAILURES)
def test_sync_errors_never_contain_token(
    make_failure: Any, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    transport = httpx.MockTransport(Recorder(make_failure()))
    client = eltoque.ElToqueClient(SECRET, transport=transport)
    with pytest.raises(exc.ElToqueError) as info:
        client.get_latest_rates()
    assert SECRET not in everything_about(info.value)
    assert SECRET not in repr(client)
    assert SECRET not in caplog.text


@pytest.mark.parametrize("make_failure", FAILURES)
async def test_async_errors_never_contain_token(
    make_failure: Any, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    transport = httpx.MockTransport(Recorder(make_failure()))
    client = eltoque.AsyncElToqueClient(SECRET, transport=transport)
    with pytest.raises(exc.ElToqueError) as info:
        await client.get_latest_rates()
    assert SECRET not in everything_about(info.value)
    assert SECRET not in repr(client)
    assert SECRET not in caplog.text


def test_success_path_does_not_log_token(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    client = eltoque.ElToqueClient(SECRET, transport=httpx.MockTransport(Recorder(json_response())))
    response = client.get_latest_rates()
    assert SECRET not in caplog.text
    assert SECRET not in repr(response)


def test_configuration_errors_do_not_echo_the_token() -> None:
    bad = SECRET + " with space"
    with pytest.raises(exc.ElToqueConfigurationError) as info:
        eltoque.ElToqueClient(bad)
    assert SECRET not in str(info.value)


@pytest.mark.parametrize(
    "token", ["a\r\nX-Injected: 1", "a\nb", "a\x00b", "a b", " a", "a ", "\ta"]
)
def test_header_injection_attempts_are_rejected(token: str) -> None:
    recorder = Recorder(json_response())
    with pytest.raises(exc.ElToqueConfigurationError):
        eltoque.ElToqueClient(token, transport=httpx.MockTransport(recorder))
    assert recorder.requests == []


def test_token_is_sent_only_in_authorization_header() -> None:
    recorder = Recorder(json_response())
    eltoque.ElToqueClient(TOKEN, transport=httpx.MockTransport(recorder)).get_latest_rates()
    request = recorder.requests[0]
    assert TOKEN not in str(request.url)
    others = {k: v for k, v in request.headers.items() if k.lower() != "authorization"}
    assert all(TOKEN not in value for value in others.values())


def test_cross_host_redirect_does_not_forward_credentials() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.host == "tasas.eltoque.com":
            return httpx.Response(307, headers={"Location": "https://evil.test/collect"})
        return httpx.Response(200, json={"leaked": True})

    client = eltoque.ElToqueClient(TOKEN, transport=httpx.MockTransport(handler))
    with pytest.raises(exc.ElToqueAPIError):
        client.get_latest_rates()
    assert [r.url.host for r in seen] == ["tasas.eltoque.com"]


async def test_cross_host_redirect_async_does_not_forward_credentials() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(301, headers={"Location": "https://evil.test/"})

    client = eltoque.AsyncElToqueClient(TOKEN, transport=httpx.MockTransport(handler))
    with pytest.raises(exc.ElToqueAPIError):
        await client.get_latest_rates()
    assert [r.url.host for r in seen] == ["tasas.eltoque.com"]


def test_plain_http_to_remote_host_is_refused() -> None:
    with pytest.raises(exc.ElToqueConfigurationError):
        eltoque.ElToqueClient(TOKEN, base_url="http://tasas.eltoque.com")
