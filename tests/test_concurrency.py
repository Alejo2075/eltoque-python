"""Concurrent use under rate limiting; the SDK must never poll or amplify traffic."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import httpx

import eltoque
from eltoque import exceptions as exc
from tests.conftest import TOKEN

if TYPE_CHECKING:
    import pytest


class LimitedServer:
    """Allows `allowed` requests, then answers 429 with Retry-After."""

    def __init__(self, allowed: int) -> None:
        self.allowed = allowed
        self.count = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.count += 1
        if self.count > self.allowed:
            return httpx.Response(
                429,
                json={"error": "limit", "limit": "60 per 1 minute"},
                headers={"Retry-After": "60", "X-RateLimit-Remaining": "0"},
            )
        return httpx.Response(200, json={"n": self.count})


async def test_concurrent_requests_hit_rate_limit_without_amplification() -> None:
    server = LimitedServer(allowed=3)
    client = eltoque.AsyncElToqueClient(TOKEN, transport=httpx.MockTransport(server))
    results = await asyncio.gather(
        *(client.get_latest_rates() for _ in range(8)), return_exceptions=True
    )
    limited = [r for r in results if isinstance(r, exc.ElToqueRateLimitError)]
    ok = [r for r in results if isinstance(r, eltoque.RatesResponse)]
    assert len(ok) == 3
    assert len(limited) == 5
    assert all(error.retry_after == 60.0 for error in limited)
    assert server.count == 8  # exactly one request per call, no hidden retries


async def test_retry_after_longer_than_cap_is_not_waited_even_with_retries() -> None:
    server = LimitedServer(allowed=0)
    client = eltoque.AsyncElToqueClient(TOKEN, transport=httpx.MockTransport(server), max_retries=5)
    results = await asyncio.gather(
        *(client.get_latest_rates() for _ in range(4)), return_exceptions=True
    )
    assert all(isinstance(r, exc.ElToqueRateLimitError) for r in results)
    assert server.count == 4  # 60s > default 30s cap: fail fast instead of burning quota


async def test_retry_traffic_is_bounded_by_max_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    async def no_sleep(delay: float) -> None:
        return None

    monkeypatch.setattr("eltoque._async_client.asyncio.sleep", no_sleep)
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503)

    client = eltoque.AsyncElToqueClient(
        TOKEN, transport=httpx.MockTransport(handler), max_retries=2
    )
    results = await asyncio.gather(
        *(client.get_latest_rates() for _ in range(5)), return_exceptions=True
    )
    assert all(isinstance(r, exc.ElToqueServerError) for r in results)
    assert calls == 5 * 3


async def test_no_background_activity_after_requests_finish() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={})

    async with eltoque.AsyncElToqueClient(TOKEN, transport=httpx.MockTransport(handler)) as client:
        await client.get_latest_rates()
        before = calls
        await asyncio.sleep(0.05)
    assert calls == before == 1


def test_sync_client_makes_one_request_per_call() -> None:
    server = LimitedServer(allowed=10)
    client = eltoque.ElToqueClient(TOKEN, transport=httpx.MockTransport(server))
    for _ in range(4):
        client.get_latest_rates()
    assert server.count == 4
