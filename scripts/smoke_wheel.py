"""Smoke test for a *built and installed* eltoque-python wheel.

Run it with the interpreter of a fresh virtualenv, from outside the repository:

    python -m venv /tmp/smoke && /tmp/smoke/bin/pip install dist/*.whl
    cd /tmp && /tmp/smoke/bin/python /path/to/scripts/smoke_wheel.py

It uses a mocked transport: no network, no token.
"""

from __future__ import annotations

import asyncio
import importlib.metadata
import importlib.resources
from pathlib import Path

import httpx

import eltoque


def main() -> None:
    location = Path(eltoque.__file__).resolve()
    assert "site-packages" in location.parts, f"not imported from an installed wheel: {location}"
    assert eltoque.__version__ == importlib.metadata.version("eltoque-python")
    assert importlib.resources.files("eltoque").joinpath("py.typed").is_file(), "py.typed missing"

    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"synthetic": True}))
    with eltoque.ElToqueClient("fake.token", transport=transport) as client:
        assert client.get_latest_rates().data == {"synthetic": True}

    async def run() -> None:
        async with eltoque.AsyncElToqueClient("fake.token", transport=transport) as aclient:
            assert (await aclient.get_latest_rates()).data == {"synthetic": True}

    asyncio.run(run())
    print(f"eltoque-python {eltoque.__version__}: wheel smoke test OK ({location.parent})")


if __name__ == "__main__":
    main()
