"""Shared test helpers. All HTTP is mocked; no network and no real token is ever used."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx
import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

TOKEN = "fake.jwt-token_123"


class Recorder:
    """Scripted MockTransport handler that records every request."""

    def __init__(self, *responses: httpx.Response | Exception) -> None:
        self._responses = list(responses)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        item = self._responses.pop(0) if len(self._responses) > 1 else self._responses[0]
        if isinstance(item, Exception):
            raise item
        return item


def json_response(payload: Any = None, status: int = 200, **headers: str) -> httpx.Response:
    return httpx.Response(
        status, json={"synthetic": True} if payload is None else payload, headers=headers
    )


@pytest.fixture
def recorder_factory() -> Callable[..., Recorder]:
    return Recorder
