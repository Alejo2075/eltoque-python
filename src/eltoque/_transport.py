"""Sync/async-neutral request building and response handling (internal)."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from eltoque._version import __version__
from eltoque.exceptions import (
    ElToqueAPIError,
    ElToqueAuthenticationError,
    ElToqueBadRequestError,
    ElToqueRateLimitError,
    ElToqueServerError,
    ElToqueUnprocessableError,
)
from eltoque.models import RateLimitInfo

if TYPE_CHECKING:
    from collections.abc import Mapping

    from eltoque._config import ClientConfig

TRMI_PATH = "/v1/trmi"
USER_AGENT = f"eltoque-python/{__version__}"
EXCERPT_LIMIT = 200

_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]+")
_ERROR_TYPES: dict[int, tuple[type[ElToqueAPIError], str]] = {
    400: (ElToqueBadRequestError, "bad request (the interval must be shorter than 24 hours)"),
    401: (ElToqueAuthenticationError, "unauthorized (the token is wrong or expired)"),
    422: (ElToqueUnprocessableError, "unprocessable entity (check the token)"),
    429: (ElToqueRateLimitError, "rate limit exceeded"),
}


def build_request_parts(
    config: ClientConfig, date_range: tuple[str, str] | None = None
) -> tuple[str, dict[str, str], dict[str, str]]:
    """Return ``(url, query_params, headers)`` for ``GET /v1/trmi``.

    Without a date range no query parameters are sent (rolling last 24 hours).
    """
    params: dict[str, str] = {}
    if date_range is not None:
        params = {"date_from": date_range[0], "date_to": date_range[1]}
    headers = {
        "Authorization": f"Bearer {config.api_token}",
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }
    return f"{config.base_url}{TRMI_PATH}", params, headers


def make_excerpt(body: bytes, token: str) -> str | None:
    """Return a short, single-line, token-free excerpt of a response body for diagnostics."""
    text = body[: EXCERPT_LIMIT * 4].decode("utf-8", errors="replace")
    text = _CONTROL_CHARS.sub(" ", text).replace(token, "***").strip()
    if not text:
        return None
    return text if len(text) <= EXCERPT_LIMIT else text[:EXCERPT_LIMIT] + "..."


def error_for_response(
    status_code: int, headers: Mapping[str, str], body: bytes, token: str
) -> ElToqueAPIError | None:
    """Map an HTTP response to an SDK exception, or ``None`` for a 2xx status."""
    if 200 <= status_code < 300:
        return None
    error_type, reason = _ERROR_TYPES.get(status_code, (ElToqueAPIError, "unexpected status"))
    if status_code >= 500:
        error_type, reason = ElToqueServerError, "server error"
    return error_type(
        f"HTTP {status_code}: {reason}",
        status_code=status_code,
        body_excerpt=make_excerpt(body, token),
        rate_limit=RateLimitInfo.from_headers(headers),
    )
