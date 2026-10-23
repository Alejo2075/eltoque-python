"""Network, DNS and timeout failure modes, including failures while streaming the body."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest

import eltoque
from eltoque import exceptions as exc
from tests.conftest import TOKEN, Recorder

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

TIMEOUTS = [
    httpx.ConnectTimeout("connect"),
    httpx.ReadTimeout("read"),
    httpx.WriteTimeout("write"),
    httpx.PoolTimeout("pool"),
]
NETWORK = [
    httpx.ConnectError("[Errno 8] nodename nor servname provided, or not known"),
    httpx.ReadError("reset"),
    httpx.WriteError("broken pipe"),
    httpx.RemoteProtocolError("bad framing"),
    httpx.ProxyError("proxy"),
]


class FailingStream(httpx.SyncByteStream, httpx.AsyncByteStream):
    """Delivers one chunk and then fails, like a connection dropped mid-body."""

    def __init__(self, error: Exception) -> None:
        self._error = error

    def __iter__(self) -> Iterator[bytes]:
        yield b'{"partial":'
        raise self._error

    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield b'{"partial":'
        raise self._error


@pytest.mark.parametrize("error", TIMEOUTS)
def test_sync_timeouts(error: Exception) -> None:
    client = eltoque.ElToqueClient(TOKEN, transport=httpx.MockTransport(Recorder(error)))
    with pytest.raises(exc.ElToqueTimeoutError):
        client.get_latest_rates()


@pytest.mark.parametrize("error", NETWORK)
def test_sync_network_errors(error: Exception) -> None:
    client = eltoque.ElToqueClient(TOKEN, transport=httpx.MockTransport(Recorder(error)))
    with pytest.raises(exc.ElToqueNetworkError):
        client.get_latest_rates()


@pytest.mark.parametrize("error", TIMEOUTS)
async def test_async_timeouts(error: Exception) -> None:
    client = eltoque.AsyncElToqueClient(TOKEN, transport=httpx.MockTransport(Recorder(error)))
    with pytest.raises(exc.ElToqueTimeoutError):
        await client.get_latest_rates()


@pytest.mark.parametrize("error", NETWORK)
async def test_async_network_errors(error: Exception) -> None:
    client = eltoque.AsyncElToqueClient(TOKEN, transport=httpx.MockTransport(Recorder(error)))
    with pytest.raises(exc.ElToqueNetworkError):
        await client.get_latest_rates()


def test_sync_failure_while_reading_body() -> None:
    response = httpx.Response(200, stream=FailingStream(httpx.ReadError("dropped")))
    client = eltoque.ElToqueClient(TOKEN, transport=httpx.MockTransport(Recorder(response)))
    with pytest.raises(exc.ElToqueNetworkError):
        client.get_latest_rates()


def test_sync_timeout_while_reading_body() -> None:
    response = httpx.Response(200, stream=FailingStream(httpx.ReadTimeout("slow")))
    client = eltoque.ElToqueClient(TOKEN, transport=httpx.MockTransport(Recorder(response)))
    with pytest.raises(exc.ElToqueTimeoutError):
        client.get_latest_rates()


async def test_async_failure_while_reading_body() -> None:
    response = httpx.Response(200, stream=FailingStream(httpx.ReadError("dropped")))
    client = eltoque.AsyncElToqueClient(TOKEN, transport=httpx.MockTransport(Recorder(response)))
    with pytest.raises(exc.ElToqueNetworkError):
        await client.get_latest_rates()


def test_error_status_with_oversized_body_still_raises_api_error() -> None:
    response = httpx.Response(500, content=b"x" * (6 * 1024 * 1024))
    client = eltoque.ElToqueClient(TOKEN, transport=httpx.MockTransport(Recorder(response)))
    with pytest.raises(exc.ElToqueServerError) as info:
        client.get_latest_rates()
    assert info.value.body_excerpt is not None
    assert len(info.value.body_excerpt) <= 203


def test_client_is_usable_after_a_failed_request() -> None:
    recorder = Recorder(httpx.ConnectError("down"), httpx.Response(200, json={"ok": 1}))
    client = eltoque.ElToqueClient(TOKEN, transport=httpx.MockTransport(recorder))
    with pytest.raises(exc.ElToqueNetworkError):
        client.get_latest_rates()
    assert client.get_latest_rates().data == {"ok": 1}


def test_custom_timeout_is_applied_to_owned_client() -> None:
    client = eltoque.ElToqueClient(TOKEN, timeout=httpx.Timeout(1.5, read=2.5))
    assert client._http.timeout == httpx.Timeout(1.5, read=2.5)
    client.close()
