"""Sync/async-neutral request building and response handling (internal)."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

from eltoque._version import __version__
from eltoque.exceptions import (
    ElToqueAPIError,
    ElToqueAuthenticationError,
    ElToqueBadRequestError,
    ElToqueDecodeError,
    ElToqueRateLimitError,
    ElToqueServerError,
    ElToqueUnprocessableError,
)
from eltoque.models import RateLimitInfo

if TYPE_CHECKING:
    from collections.abc import Mapping

    import httpx

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


def _too_large(limit: int) -> ElToqueDecodeError:
    return ElToqueDecodeError(f"response body exceeds the {limit}-byte limit")


def check_declared_length(headers: Mapping[str, str], limit: int, *, strict: bool) -> None:
    """Reject early when ``Content-Length`` already exceeds ``limit`` (strict mode only)."""
    declared = headers.get("content-length", "")
    if strict and declared.isascii() and declared.isdigit() and int(declared) > limit:
        raise _too_large(limit)


def read_limited(response: httpx.Response, limit: int, *, strict: bool = True) -> bytes:
    """Read a streamed body. Over ``limit``: raise (strict) or truncate (non-strict)."""
    check_declared_length(response.headers, limit, strict=strict)
    chunks: list[bytes] = []
    size = 0
    for chunk in response.iter_bytes():
        size += len(chunk)
        if size > limit:
            if strict:
                raise _too_large(limit)
            chunks.append(chunk[: len(chunk) - (size - limit)])
            break
        chunks.append(chunk)
    return b"".join(chunks)


async def aread_limited(response: httpx.Response, limit: int, *, strict: bool = True) -> bytes:
    """Async twin of :func:`read_limited`."""
    check_declared_length(response.headers, limit, strict=strict)
    chunks: list[bytes] = []
    size = 0
    async for chunk in response.aiter_bytes():
        size += len(chunk)
        if size > limit:
            if strict:
                raise _too_large(limit)
            chunks.append(chunk[: len(chunk) - (size - limit)])
            break
        chunks.append(chunk)
    return b"".join(chunks)


def decode_json(body: bytes) -> Any:
    """Decode a JSON body exactly as sent; never substitute ``{}`` for bad input."""
    if not body.strip():
        raise ElToqueDecodeError("the response body is empty; expected JSON")
    try:
        return json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ElToqueDecodeError("the response body is not valid JSON") from error
