"""README/guide snippets and example scripts must run against the real public API.

All network traffic is replaced by a canned synthetic response: no token, no Internet.
"""

from __future__ import annotations

import re
import runpy
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator

ROOT = Path(__file__).resolve().parent.parent
DOC_FILES = [
    "README.md",
    "docs/quickstart.es.md",
    "docs/configuration.md",
    "docs/errors.md",
]
EXAMPLES = sorted((ROOT / "examples").glob("*.py")) if (ROOT / "examples").exists() else []
FENCE = re.compile(r"```python\n(.*?)```", re.DOTALL)


def _snippets() -> Iterator[pytest.param]:  # type: ignore[valid-type]
    for name in DOC_FILES:
        path = ROOT / name
        if not path.exists():
            continue
        for index, code in enumerate(FENCE.findall(path.read_text(encoding="utf-8"))):
            yield pytest.param(code, id=f"{name}#{index}")


@pytest.fixture(autouse=True)
def mocked_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def handle(self: httpx.HTTPTransport, request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"synthetic": True}, headers={"X-RateLimit-Remaining": "59"}
        )

    async def ahandle(self: httpx.AsyncHTTPTransport, request: httpx.Request) -> httpx.Response:
        return handle(self, request)  # type: ignore[arg-type]

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", handle)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", ahandle)
    monkeypatch.setenv("ELTOQUE_API_TOKEN", "fake.token")


@pytest.mark.parametrize("code", list(_snippets()))
def test_documentation_snippet_runs(code: str, capsys: pytest.CaptureFixture[str]) -> None:
    exec(compile(code, "<doc-snippet>", "exec"), {"__name__": "__main__"})  # noqa: S102
    assert "Traceback" not in capsys.readouterr().err


def test_documentation_has_snippets() -> None:
    assert len(list(_snippets())) >= 8


@pytest.mark.parametrize("script", EXAMPLES, ids=lambda p: p.name)
def test_example_script_runs(script: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runpy.run_path(str(script), run_name="__main__")
    assert "synthetic" in capsys.readouterr().out
