"""Fetch rates for an explicit window shorter than 24 hours.

The API's time zone is undocumented, so naive datetimes are sent exactly as written.
Run: ELTOQUE_API_TOKEN=... python examples/date_range.py
"""

import os
from datetime import datetime

from eltoque import ElToqueClient


def main() -> None:
    with ElToqueClient(api_token=os.environ["ELTOQUE_API_TOKEN"]) as client:
        response = client.get_rates(
            datetime(2022, 10, 27, 0, 0, 0),
            datetime(2022, 10, 27, 23, 59, 59),
        )
    print(response.data)
    print("Source: elTOQUE (reference estimates, not official rates)")


if __name__ == "__main__":
    main()
