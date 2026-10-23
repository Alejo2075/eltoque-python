"""Fetch the latest elTOQUE rates (rolling last 24 hours).

Run: ELTOQUE_API_TOKEN=... python examples/basic.py
"""

import os

from eltoque import ATTRIBUTION, ElToqueClient, ElToqueError


def main() -> None:
    with ElToqueClient(api_token=os.environ["ELTOQUE_API_TOKEN"]) as client:
        try:
            response = client.get_latest_rates()
        except ElToqueError as error:
            raise SystemExit(f"elTOQUE request failed: {error}") from None
    print(response.data)  # the provider's JSON, untouched
    for code, value in response.rates.rates.items():  # typed view: code -> Decimal
        print(f"{code}: {value}")
    print(ATTRIBUTION)


if __name__ == "__main__":
    main()
