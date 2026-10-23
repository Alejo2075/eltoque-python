"""Public exception hierarchy.

Messages never contain the API token. Response bodies are not included in messages;
``body_excerpt`` holds a short, sanitized excerpt for diagnostics only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from eltoque.models import RateLimitInfo


class ElToqueError(Exception):
    """Base class for every error raised by this SDK."""


class ElToqueConfigurationError(ElToqueError):
    """Invalid client configuration (token, base URL, timeout, retries)."""


class ElToqueValidationError(ElToqueError):
    """Invalid call arguments, detected before any HTTP request is made."""


class ElToqueNetworkError(ElToqueError):
    """The request could not be completed (connection, DNS, TLS, protocol)."""


class ElToqueTimeoutError(ElToqueError):
    """The request timed out."""


class ElToqueDecodeError(ElToqueError):
    """A successful response did not contain valid JSON, or exceeded the size limit."""


class ElToqueAPIError(ElToqueError):
    """The API answered with an unexpected or error HTTP status."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        body_excerpt: str | None = None,
        rate_limit: RateLimitInfo | None = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body_excerpt = body_excerpt
        self.rate_limit = rate_limit
        if retry_after is None and rate_limit is not None:
            retry_after = rate_limit.retry_after
        self.retry_after = retry_after


class ElToqueBadRequestError(ElToqueAPIError):
    """HTTP 400, e.g. a date range of 24 hours or more."""


class ElToqueAuthenticationError(ElToqueAPIError):
    """HTTP 401: the token is wrong or expired."""


class ElToqueUnprocessableError(ElToqueAPIError):
    """HTTP 422: unprocessable entity; check the token."""


class ElToqueRateLimitError(ElToqueAPIError):
    """HTTP 429: the API key exceeded its rate limit. See ``retry_after``."""


class ElToqueServerError(ElToqueAPIError):
    """HTTP 5xx."""
