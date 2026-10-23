"""Sync/async-neutral request building and response handling (internal)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from eltoque._version import __version__

if TYPE_CHECKING:
    from eltoque._config import ClientConfig

TRMI_PATH = "/v1/trmi"
USER_AGENT = f"eltoque-python/{__version__}"


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
