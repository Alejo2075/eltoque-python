"""Response models owned by the SDK.

The published OpenAPI document does not define the HTTP 200 body. ``RatesResponse.data`` therefore
always exposes the decoded payload untouched. ``Rates`` is a *validated, typed view* built from the
shape observed against the live API on 2026-10-23 (see docs/api-contract.md); it is optional and
raises ``ElToqueDecodeError`` when the payload does not match, instead of guessing.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from eltoque.exceptions import ElToqueDecodeError

if TYPE_CHECKING:
    from collections.abc import Mapping

ATTRIBUTION = "Source: elTOQUE. Exchange rates are indicative, not official."


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


def _to_decimal(code: str, value: Any) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ElToqueDecodeError(f"rate for {code!r} is not a number")
    if isinstance(value, float) and not math.isfinite(value):
        raise ElToqueDecodeError(f"rate for {code!r} is not finite")
    # repr() is the shortest string that round-trips the JSON number, so no float noise is added.
    return Decimal(repr(value))


def _require_int(name: str, value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ElToqueDecodeError(f"{name!r} is missing or not an integer")
    return value


@dataclass(frozen=True, slots=True)
class Rates:
    """Typed view of a successful ``GET /v1/trmi`` payload.

    ``rates`` maps the provider's currency/asset code (e.g. ``"USD"``) to a ``Decimal``. The set
    of codes is open: the provider can add or drop codes, so look them up defensively.
    ``reported_at`` is the timestamp the provider put in the response (``date``, ``hour``,
    ``minutes``, ``seconds``) as a *naive* datetime; its time zone is undocumented (it was
    observed near UTC-4) and it is not the requested window.

    Values are the provider's, unmodified; nothing is rounded or converted. Exchange rates are
    indicative, not official. Source: elTOQUE.
    """

    rates: Mapping[str, Decimal]
    reported_at: datetime

    @classmethod
    def from_payload(cls, payload: Any) -> Rates:
        """Validate ``payload`` (the decoded JSON) and build a :class:`Rates`.

        Raises :class:`~eltoque.exceptions.ElToqueDecodeError` if it does not have the confirmed
        shape. Unknown extra top-level keys are ignored (they stay available in ``data``).
        """
        if not isinstance(payload, dict):
            raise ElToqueDecodeError("expected a JSON object with a 'tasas' mapping")
        tasas = payload.get("tasas")
        if not isinstance(tasas, dict) or not tasas:
            raise ElToqueDecodeError("'tasas' is missing, empty or not an object")
        rates = {str(code): _to_decimal(str(code), value) for code, value in tasas.items()}
        raw_date = payload.get("date")
        try:
            if not isinstance(raw_date, str):
                raise ValueError
            day = date.fromisoformat(raw_date)
            reported_at = datetime(
                day.year,
                day.month,
                day.day,
                _require_int("hour", payload.get("hour")),
                _require_int("minutes", payload.get("minutes")),
                _require_int("seconds", payload.get("seconds")),
            )
        except ValueError:
            raise ElToqueDecodeError("the response timestamp is missing or invalid") from None
        return cls(rates=MappingProxyType(rates), reported_at=reported_at)


@dataclass(frozen=True, slots=True)
class RatesResponse:
    """Envelope around a successful ``GET /v1/trmi`` response.

    ``data`` is the decoded JSON body, untouched: the provider has not published a schema for
    HTTP 200, so no field names are guaranteed. ``status_code``, ``rate_limit`` and
    ``received_at`` are SDK metadata, not provider fields.

    Exchange rates are indicative, not official. Source: elTOQUE.
    """

    data: Any
    status_code: int = 200
    rate_limit: RateLimitInfo = field(default_factory=RateLimitInfo)
    received_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def rates(self) -> Rates:
        """Validated typed view of :attr:`data` (raises ``ElToqueDecodeError`` on a mismatch)."""
        return Rates.from_payload(self.data)
