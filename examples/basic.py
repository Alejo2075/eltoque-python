"""Fetch the latest elTOQUE rates (rolling last 24 hours).

Exchange rates are indicative, not official. Source: elTOQUE.
Run: ELTOQUE_API_TOKEN=... python examples/basic.py
"""

import os

from eltoque import ElToqueClient, ElToqueError


def main() -> None:
    with ElToqueClient(api_token=os.environ["ELTOQUE_API_TOKEN"]) as client:
        try:
            response = client.get_latest_rates()
        except ElToqueError as error:
            raise SystemExit(f"elTOQUE request failed: {error}") from None
    print(response.data)  # original provider JSON; its schema is not published
    print("Source: elTOQUE (reference estimates, not official rates)")


if __name__ == "__main__":
    main()
