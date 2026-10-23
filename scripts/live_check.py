"""Opt-in live check against the real elTOQUE API (one request, nothing stored).

    ELTOQUE_API_TOKEN=... ELTOQUE_ALLOW_LIVE_TESTS=1 python scripts/live_check.py

Refuses to run unless BOTH variables are set: the token must be the one you registered for this
application and you must explicitly accept spending one request of its quota.

It prints only the *shape* of the response (types, keys, list lengths, decimal places), whether the
typed ``Rates`` view parses it, the HTTP status and the rate-limit metadata. Provider values
are never printed, so the output can be pasted into docs/api-contract.md without
redistributing elTOQUE data. Review it before sharing: object keys are shown as-is, and a key
could itself be data.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

import eltoque

MAX_DEPTH = 6
MAX_ITEMS = 25


def describe_shape(value: Any, depth: int = 0) -> Any:
    """Return a value-free description of ``value`` (types, keys and sizes only)."""
    if depth >= MAX_DEPTH:
        return "<max depth>"
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        decimals = len(repr(value).partition(".")[2]) if "e" not in repr(value) else "exp"
        return f"float(decimals={decimals})"
    if isinstance(value, str):
        return f"str(len={len(value)})"
    if isinstance(value, list):
        sample = [describe_shape(item, depth + 1) for item in value[:MAX_ITEMS]]
        return {"list": len(value), "items": sample}
    if isinstance(value, dict):
        shown = list(value.items())[:MAX_ITEMS]
        described = {str(key): describe_shape(item, depth + 1) for key, item in shown}
        if len(value) > MAX_ITEMS:
            described["<more keys>"] = len(value) - MAX_ITEMS
        return described
    return type(value).__name__


def main() -> int:
    token = os.environ.get("ELTOQUE_API_TOKEN", "")
    if not token or os.environ.get("ELTOQUE_ALLOW_LIVE_TESTS") != "1":
        print(
            "Refusing to run: set ELTOQUE_API_TOKEN and ELTOQUE_ALLOW_LIVE_TESTS=1 "
            "(this makes one real request and uses your quota).",
            file=sys.stderr,
        )
        return 2
    try:
        with eltoque.ElToqueClient(token) as client:
            response = client.get_latest_rates()
    except eltoque.ElToqueError as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        return 1
    try:
        typed: dict[str, Any] = {"ok": True, "codes": sorted(response.rates.rates)}
    except eltoque.ElToqueDecodeError as error:
        typed = {"ok": False, "error": str(error)}
    report = {
        "status_code": response.status_code,
        "rate_limit": {
            "limit": response.rate_limit.limit,
            "remaining": response.rate_limit.remaining,
            "reset": response.rate_limit.reset,
        },
        "typed_parse": typed,
        "shape": describe_shape(response.data),
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
