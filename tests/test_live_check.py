"""The live-check helper must be inert without authorization and never leak provider values."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import httpx
import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "live_check.py"
spec = importlib.util.spec_from_file_location("live_check", SCRIPT)
assert spec is not None
assert spec.loader is not None
live_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(live_check)


@pytest.mark.parametrize(
    "env",
    [{}, {"ELTOQUE_API_TOKEN": "fake.token"}, {"ELTOQUE_ALLOW_LIVE_TESTS": "1"}],
)
def test_refuses_without_both_variables(
    env: dict[str, str], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("ELTOQUE_API_TOKEN", raising=False)
    monkeypatch.delenv("ELTOQUE_ALLOW_LIVE_TESTS", raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    def boom(*args: object, **kwargs: object) -> None:
        raise AssertionError("no network allowed")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", boom)
    assert live_check.main() == 2
    assert "Refusing" in capsys.readouterr().err


def test_prints_shape_but_never_values(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("ELTOQUE_API_TOKEN", "fake.token")
    monkeypatch.setenv("ELTOQUE_ALLOW_LIVE_TESTS", "1")
    payload = {"rates": [{"code": "SECRETVALUE", "price": 365.25}], "n": 3, "ok": True, "x": None}
    calls = []

    def handle(self: httpx.HTTPTransport, request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=payload, headers={"X-RateLimit-Remaining": "59"})

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", handle)
    assert live_check.main() == 0
    out = capsys.readouterr().out
    assert len(calls) == 1
    assert "SECRETVALUE" not in out
    assert "365.25" not in out
    assert "fake.token" not in out
    assert "float(decimals=2)" in out
    assert '"remaining": 59' in out


def test_api_error_exits_nonzero_without_leaking(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("ELTOQUE_API_TOKEN", "fake.token")
    monkeypatch.setenv("ELTOQUE_ALLOW_LIVE_TESTS", "1")
    monkeypatch.setattr(
        httpx.HTTPTransport,
        "handle_request",
        lambda self, request: httpx.Response(401, text="fake.token rejected"),
    )
    assert live_check.main() == 1
    captured = capsys.readouterr()
    assert "ElToqueAuthenticationError" in captured.err
    assert "fake.token" not in captured.err + captured.out


def test_shape_limits_depth_and_size() -> None:
    deep: object = 1
    for _ in range(20):
        deep = [deep]
    assert "<max depth>" in str(live_check.describe_shape(deep))
    big = {f"k{i}": i for i in range(100)}
    assert live_check.describe_shape(big)["<more keys>"] == 100 - live_check.MAX_ITEMS
    assert live_check.describe_shape(1e-7) == "float(decimals=exp)"
    assert live_check.describe_shape(object()) == "object"
