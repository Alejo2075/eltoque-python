# Validating against the real API

The test suite never touches the real elTOQUE API. This page is the checklist for the first time
you have **your own approved token** (request it at <https://tasas-token.eltoque.com/>). It is
meant to close the items listed as unverified in [api-contract.md](api-contract.md).

Ground rules: use only your own application's token, keep the number of requests tiny (default
limit: 60/minute, 10/second), never commit tokens or real responses, and do not redistribute
the data (see the [terms of use](https://eltoque.com/api-tasas-de-eltoque-terminos-y-condiciones-de-uso)).

## 1. Smoke check: does the client work? (1 request)

```bash
export ELTOQUE_API_TOKEN="your-application-token"
export ELTOQUE_ALLOW_LIVE_TESTS=1
python scripts/live_check.py
```

It refuses to run unless both variables are set, makes **one** request and prints:

- the HTTP status and rate-limit headers (`limit`, `remaining`, `reset`);
- the **shape** of the JSON (types, keys, list sizes, decimal places) and **no values**.

Exit codes: `0` ok, `1` the API or network failed (error class and message shown), `2` not
authorized to run.

Or run the opt-in pytest check (also one request): `uv run pytest -m integration --no-cov`.

## 2. Record what you learn

From the shape output, fill in the "Unverified / unknown" checklist in
[api-contract.md](api-contract.md) with a validation date:

- [ ] Top-level type (object or list) and field names; which are currencies.
- [ ] Types and decimal places of the rate values (decides `Decimal` vs. `float`).
- [ ] Whether there are timestamps, and in which format.
- [ ] What `X-RateLimit-Reset` means (compare it with the current time on two consecutive calls).

Paste only the value-free shape. Review it first: object keys are printed as-is.

## 3. Time zone and ranges (2-3 more requests, done by hand)

The API does not document its time zone. With a short Python session:

```python
import os
from datetime import datetime, timedelta

from eltoque import ElToqueClient

with ElToqueClient(os.environ["ELTOQUE_API_TOKEN"]) as client:
    now = datetime.now()  # your local, naive time
    r1 = client.get_rates(now - timedelta(hours=2), now - timedelta(hours=1))
    print(type(r1.data), r1.rate_limit)
```

Compare windows shifted by the suspected offset and see which returns data for the period you
expect. Also confirm what happens with a window of exactly 24 hours (expected: HTTP 400, which the
SDK already rejects before sending) and with only one bound (the SDK refuses this today).

## 4. What was done with the findings

The first validation (2026-10-23) produced the typed `Rates` view and the notes in
[api-contract.md](api-contract.md). When you re-run this check later, `typed_parse.ok` in the output
tells you whether the provider's payload still matches. If it does not, update the contract notes
and `Rates.from_payload`, add synthetic fixtures for the new shape, and follow
[publishing.md](publishing.md).
