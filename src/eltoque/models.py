"""Response models owned by the SDK.

Nothing in this module describes provider fields: the published OpenAPI document does not
define the HTTP 200 body, so the payload is exposed exactly as decoded.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping


def _parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    text = value.strip()
    if not text.isascii() or not text.isdigit():
        return None
    return int(text)


def _parse_seconds(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        seconds = float(value.strip())
    except ValueError:
        return None
    if not math.isfinite(seconds) or seconds < 0:
        return None
    return seconds


@dataclass(frozen=True, slots=True)
class RateLimitInfo:
    """Rate-limit metadata parsed from response headers.

    Every field is optional: missing or malformed headers yield ``None`` and never raise.
    ``reset`` is kept as the raw integer sent by the provider; its unit is not documented.
    """

    limit: int | None = None
    remaining: int | None = None
    reset: int | None = None
    retry_after: float | None = None

    @classmethod
    def from_headers(cls, headers: Mapping[str, str]) -> RateLimitInfo:
        """Build an instance from response headers (names are matched case-insensitively)."""
        lowered = {key.lower(): value for key, value in headers.items()}
        return cls(
            limit=_parse_int(lowered.get("x-ratelimit-limit")),
            remaining=_parse_int(lowered.get("x-ratelimit-remaining")),
            reset=_parse_int(lowered.get("x-ratelimit-reset")),
            retry_after=_parse_seconds(lowered.get("retry-after")),
        )
