"""Async variant of basic.py.

Run: ELTOQUE_API_TOKEN=... python examples/async_basic.py
"""

import asyncio
import os

from eltoque import ATTRIBUTION, AsyncElToqueClient


async def main() -> None:
    async with AsyncElToqueClient(api_token=os.environ["ELTOQUE_API_TOKEN"]) as client:
        response = await client.get_latest_rates()
    print(response.data)
    for code, value in response.rates.rates.items():
        print(f"{code}: {value}")
    print(ATTRIBUTION)


if __name__ == "__main__":
    asyncio.run(main())
