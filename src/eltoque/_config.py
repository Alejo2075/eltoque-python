"""Validated, immutable client configuration (internal)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import httpx

from eltoque.exceptions import ElToqueConfigurationError

DEFAULT_TIMEOUT = httpx.Timeout(10.0, connect=5.0)
MAX_RETRIES_LIMIT = 5
DEFAULT_MAX_RETRY_DELAY = 30.0
DEFAULT_MAX_TOTAL_RETRY_DELAY = 60.0
DEFAULT_MAX_RESPONSE_BYTES = 5 * 1024 * 1024


def _validate_token(token: object) -> str:
    if not isinstance(token, str) or not token:
        raise ElToqueConfigurationError("api_token must be a non-empty string")
    # Printable ASCII without whitespace: blocks header injection and "Bearer " prefixes.
    if not all("!" <= char <= "~" for char in token):
        raise ElToqueConfigurationError(
            "api_token contains whitespace, control or non-ASCII characters; "
            "pass the bare token without a 'Bearer ' prefix"
        )
    return token


def _validate_timeout(timeout: object) -> httpx.Timeout:
    if isinstance(timeout, httpx.Timeout):
        return timeout
    if isinstance(timeout, bool) or not isinstance(timeout, int | float):
        raise ElToqueConfigurationError("timeout must be a positive number or httpx.Timeout")
    if not math.isfinite(timeout) or timeout <= 0:
        raise ElToqueConfigurationError("timeout must be a positive, finite number of seconds")
    return httpx.Timeout(float(timeout))


def _validate_non_negative(name: str, value: object, *, integer: bool = False) -> None:
    kinds = int if integer else (int, float)
    if isinstance(value, bool) or not isinstance(value, kinds):
        raise ElToqueConfigurationError(f"{name} must be a number")
    if not math.isfinite(value) or value < 0:
        raise ElToqueConfigurationError(f"{name} must be a finite number >= 0")


@dataclass(frozen=True, slots=True, repr=False)
class ClientConfig:
    """Settings shared by the sync and async clients. The token is never shown in ``repr``."""

    api_token: str
    timeout: httpx.Timeout | float = field(default_factory=lambda: DEFAULT_TIMEOUT)
    max_retries: int = 0
    max_retry_delay: float = DEFAULT_MAX_RETRY_DELAY
    max_total_retry_delay: float = DEFAULT_MAX_TOTAL_RETRY_DELAY
    max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES

    def __post_init__(self) -> None:
        object.__setattr__(self, "api_token", _validate_token(self.api_token))
        object.__setattr__(self, "timeout", _validate_timeout(self.timeout))
        _validate_non_negative("max_retries", self.max_retries, integer=True)
        if self.max_retries > MAX_RETRIES_LIMIT:
            raise ElToqueConfigurationError(f"max_retries must be <= {MAX_RETRIES_LIMIT}")
        _validate_non_negative("max_retry_delay", self.max_retry_delay)
        _validate_non_negative("max_total_retry_delay", self.max_total_retry_delay)
        _validate_non_negative("max_response_bytes", self.max_response_bytes, integer=True)
        if self.max_response_bytes == 0:
            raise ElToqueConfigurationError("max_response_bytes must be > 0")

    def __repr__(self) -> str:
        return (
            f"ClientConfig(api_token='***', timeout={self.timeout!r}, "
            f"max_retries={self.max_retries})"
        )
