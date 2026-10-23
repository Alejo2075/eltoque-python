"""Asynchronous client. Mirrors :class:`eltoque.ElToqueClient`."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Self

import httpx

from eltoque._config import DEFAULT_BASE_URL, DEFAULT_TIMEOUT, ClientConfig
from eltoque._dates import day_range, validate_range
from eltoque._retry import RetryPolicy
from eltoque._transport import (
    FOLLOW_REDIRECTS,
    aread_limited,
    build_request_parts,
    parse_response,
    translate_exception,
)
from eltoque.exceptions import ElToqueConfigurationError, ElToqueError

if TYPE_CHECKING:
    from datetime import date, datetime
    from types import TracebackType

    from eltoque.models import RatesResponse


class AsyncElToqueClient:
    """Async client for the elTOQUE ``GET /v1/trmi`` endpoint.

    Exchange rates are indicative, not official. Source: elTOQUE. Every request is made
    explicitly by the caller; nothing polls in the background.
    """

    def __init__(
        self,
        api_token: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
        max_retries: int = 0,
        transport: httpx.AsyncBaseTransport | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Create a client.

        ``max_retries`` (default 0, max 5) opts in to bounded retries for 429, 502/503/504 and
        transport failures; every retry consumes API quota. ``Retry-After`` is honored and
        waits use ``asyncio.sleep`` so cancellation propagates immediately.

        ``transport`` is a test seam (e.g. ``httpx.MockTransport``). ``http_client`` lets you
        share your own ``httpx.AsyncClient``: it is never closed by this SDK, its own timeout
        applies (``timeout`` is ignored) and redirects are still not followed for our requests.
        """
        self._config = ClientConfig(
            api_token=api_token, base_url=base_url, timeout=timeout, max_retries=max_retries
        )
        if http_client is not None and transport is not None:
            raise ElToqueConfigurationError("pass either http_client or transport, not both")
        self._owns_http = http_client is None
        self._http = http_client or httpx.AsyncClient(
            timeout=self._config.timeout, follow_redirects=FOLLOW_REDIRECTS, transport=transport
        )
        self._closed = False

    async def __aenter__(self) -> Self:
        self._ensure_open()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.aclose()

    def __repr__(self) -> str:
        return f"AsyncElToqueClient(base_url={self._config.base_url!r})"

    async def get_latest_rates(self) -> RatesResponse:
        """Rates for the rolling last 24 hours, computed by the provider at request time."""
        return await self._get(None)

    async def get_rates(self, date_from: datetime, date_to: datetime) -> RatesResponse:
        """Rates for an explicit window shorter than 24 hours (naive datetimes only)."""
        return await self._get(validate_range(date_from, date_to))

    async def get_rates_for_day(self, day: date) -> RatesResponse:
        """Convenience for ``get_rates(day 00:00:00, day 23:59:59)``; one request, no loops."""
        return await self.get_rates(*day_range(day))

    async def aclose(self) -> None:
        """Release the connection pool (only if this client created it). Idempotent."""
        if not self._closed:
            self._closed = True
            if self._owns_http:
                await self._http.aclose()

    def _ensure_open(self) -> None:
        if self._closed:
            raise ElToqueError("this client is closed; create a new AsyncElToqueClient")

    async def _get(self, date_range: tuple[str, str] | None) -> RatesResponse:
        self._ensure_open()
        policy = RetryPolicy.from_config(self._config)
        while True:
            try:
                return await self._get_once(date_range)
            except ElToqueError as error:
                delay = policy.next_delay(error)
                if delay is None:
                    raise
                await asyncio.sleep(delay)

    async def _get_once(self, date_range: tuple[str, str] | None) -> RatesResponse:
        url, params, headers = build_request_parts(self._config, date_range)
        request = self._http.build_request("GET", url, params=params or None, headers=headers)
        try:
            response = await self._http.send(
                request, stream=True, follow_redirects=FOLLOW_REDIRECTS
            )
            try:
                ok = 200 <= response.status_code < 300
                body = await aread_limited(response, self._config.max_response_bytes, strict=ok)
            finally:
                await response.aclose()
        except httpx.HTTPError as error:
            raise translate_exception(error) from None
        return parse_response(self._config, response.status_code, response.headers, body)
