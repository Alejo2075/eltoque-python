"""Opt-in checks against the real elTOQUE API.

Skipped unless BOTH are set:

* ``ELTOQUE_API_TOKEN``: a token the repository owner registered for this application;
* ``ELTOQUE_ALLOW_LIVE_TESTS=1``: explicit authorization to spend quota on the real API.

Run with ``pytest -m integration --no-cov``. Never enabled in CI. The response body is never
printed or stored: it is provider data that may not be redistributed.
"""

from __future__ import annotations

import os

import pytest

import eltoque

pytestmark = pytest.mark.integration

TOKEN = os.environ.get("ELTOQUE_API_TOKEN", "")
AUTHORIZED = os.environ.get("ELTOQUE_ALLOW_LIVE_TESTS") == "1"


@pytest.fixture(autouse=True)
def _require_authorization() -> None:
    if not (TOKEN and AUTHORIZED):
        pytest.skip("live tests need ELTOQUE_API_TOKEN and ELTOQUE_ALLOW_LIVE_TESTS=1")


def test_latest_rates_returns_decodable_json() -> None:
    with eltoque.ElToqueClient(TOKEN) as client:
        response = client.get_latest_rates()
    assert response.status_code == 200
    assert response.data is not None
