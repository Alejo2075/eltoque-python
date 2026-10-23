"""Synchronous client."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx

from eltoque._config import DEFAULT_BASE_URL, DEFAULT_TIMEOUT, ClientConfig
from eltoque._dates import validate_range
from eltoque._transport import (
    FOLLOW_REDIRECTS,
    build_request_parts,
    parse_response,
    read_limited,
    translate_exception,
)

if TYPE_CHECKING:
    from datetime import datetime

    from eltoque.models import RatesResponse


class ElToqueClient:
    """Client for the elTOQUE ``GET /v1/trmi`` endpoint.

    Exchange rates are indicative, not official. Source: elTOQUE. Every request is made
    explicitly by the caller; nothing polls in the background.
    """

    def __init__(
        self,
        api_token: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._config = ClientConfig(api_token=api_token, base_url=base_url, timeout=timeout)
        self._http = httpx.Client(
            timeout=self._config.timeout, follow_redirects=FOLLOW_REDIRECTS, transport=transport
        )

    def __repr__(self) -> str:
        return f"ElToqueClient(base_url={self._config.base_url!r})"

    def get_latest_rates(self) -> RatesResponse:
        """Rates for the rolling last 24 hours, computed by the provider at request time."""
        return self._get(None)

    def get_rates(self, date_from: datetime, date_to: datetime) -> RatesResponse:
        """Rates for an explicit window shorter than 24 hours.

        Both bounds must be naive datetimes, sent as ``YYYY-MM-DD HH:MM:SS``. The provider's
        time zone is undocumented, so no conversion is applied.
        """
        return self._get(validate_range(date_from, date_to))

    def close(self) -> None:
        """Release the underlying connection pool."""
        self._http.close()

    def _get(self, date_range: tuple[str, str] | None) -> RatesResponse:
        url, params, headers = build_request_parts(self._config, date_range)
        request = self._http.build_request("GET", url, params=params or None, headers=headers)
        try:
            response = self._http.send(request, stream=True, follow_redirects=FOLLOW_REDIRECTS)
            try:
                ok = 200 <= response.status_code < 300
                body = read_limited(response, self._config.max_response_bytes, strict=ok)
            finally:
                response.close()
        except httpx.HTTPError as error:
            raise translate_exception(error) from error
        return parse_response(self._config, response.status_code, response.headers, body)
