<p align="center">
  <img src="https://raw.githubusercontent.com/Alejo2075/eltoque-python/main/assets/logo.png" alt="eltoque-python" width="480">
</p>

**Unofficial Python SDK for elTOQUE exchange-rate data.**
A modern, typed client for the official elTOQUE exchange-rate API, with sync and async interfaces.

[![PyPI](https://img.shields.io/pypi/v/eltoque-python)](https://pypi.org/project/eltoque-python/)
[![Python](https://img.shields.io/pypi/pyversions/eltoque-python)](https://pypi.org/project/eltoque-python/)
[![CI](https://github.com/Alejo2075/eltoque-python/actions/workflows/ci.yml/badge.svg)](https://github.com/Alejo2075/eltoque-python/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

> **Independent project.** `eltoque-python` is community-maintained. It is not developed,
> sponsored, endorsed or supported by elTOQUE.
>
> **Exchange rates are indicative, not official. Source: elTOQUE.
> Access requires registration and an application-specific API token.**

```python
import os

from eltoque import ElToqueClient

with ElToqueClient(api_token=os.environ["ELTOQUE_API_TOKEN"]) as client:
    response = client.get_latest_rates()
    print(response.data)  # the provider's JSON, untouched
```

Leer en español: [docs/quickstart.es.md](docs/quickstart.es.md)

## Why use it?

- **Sync and async** clients with the same methods and behavior.
- **Typed** public API (`py.typed`, checked with `mypy --strict`).
- **Safe by default:** HTTPS only, explicit timeouts, no redirects followed (your token is never
  forwarded to another host), bounded response size, and the token never appears in `repr`,
  error messages or logs.
- **Predictable errors:** one exception family, one subclass per documented HTTP status.
- **Rate-limit aware:** parses `X-RateLimit-*` and `Retry-After`; retries are opt-in and bounded.
- **Pure Python**, one runtime dependency ([`httpx`](https://www.python-httpx.org/)), works in
  plain scripts, notebooks, Django, Flask, FastAPI or AWS Lambda.
- **Tested offline** with mocked HTTP: no token needed to develop or run the test suite.

## Installation

```bash
pip install eltoque-python
```

Requires Python 3.11 or newer. To work on the SDK itself, install from a clone with `pip install -e .`.

## Get your API token

The SDK does not grant API access. Each application that integrates the API needs **its own
token**, requested from elTOQUE:

1. Fill in the official form: <https://tasas-token.eltoque.com/>
2. Read the [terms of use](https://eltoque.com/api-tasas-de-eltoque-terminos-y-condiciones-de-uso).
3. Keep the token secret and read it from the environment:

```bash
export ELTOQUE_API_TOKEN="your-application-token"
```

Never commit a token, share it with third parties, or ship it in a browser bundle.

## Quickstart

### Latest rates (rolling last 24 hours)

```python
import os

from eltoque import ElToqueClient

with ElToqueClient(api_token=os.environ["ELTOQUE_API_TOKEN"]) as client:
    response = client.get_latest_rates()
    print(response.data)
```

### Typed rates

`response.data` is always the provider's JSON, untouched. `response.rates` is an optional,
validated view of the shape confirmed against the live API: currency codes mapped to `Decimal`.

```python
import os

from eltoque import ATTRIBUTION, ElToqueClient

with ElToqueClient(api_token=os.environ["ELTOQUE_API_TOKEN"]) as client:
    rates = client.get_latest_rates().rates

usd = rates.rates.get("USD")  # Decimal or None: the set of codes is open
print(usd, rates.reported_at)
print(ATTRIBUTION)  # "Source: elTOQUE. Exchange rates are indicative, not official."
```

### A specific window (shorter than 24 hours)

```python
import os
from datetime import datetime

from eltoque import ElToqueClient

with ElToqueClient(api_token=os.environ["ELTOQUE_API_TOKEN"]) as client:
    response = client.get_rates(
        datetime(2022, 10, 27, 0, 0, 0),
        datetime(2022, 10, 27, 23, 59, 59),
    )
    print(response.data)
```

### Async

```python
import asyncio
import os

from eltoque import AsyncElToqueClient


async def main() -> None:
    async with AsyncElToqueClient(api_token=os.environ["ELTOQUE_API_TOKEN"]) as client:
        response = await client.get_latest_rates()
        print(response.data)


asyncio.run(main())
```

### Handling errors

```python
import os

from eltoque import ElToqueClient, ElToqueError, ElToqueRateLimitError

with ElToqueClient(api_token=os.environ["ELTOQUE_API_TOKEN"], max_retries=2) as client:
    try:
        response = client.get_latest_rates()
    except ElToqueRateLimitError as error:
        print(f"Rate limited, retry in {error.retry_after} s")
    except ElToqueError as error:
        print(f"Request failed: {error}")
    else:
        print(response.rate_limit.remaining, "requests left in this window")
```

## API reference

### Clients

`ElToqueClient` (sync) and `AsyncElToqueClient` (async, `await` every method) share this
constructor:

| Parameter | Default | Description |
| --- | --- | --- |
| `api_token` | required | Your application token. Printable ASCII, no spaces, no `Bearer ` prefix. |
| `base_url` | `https://tasas.eltoque.com` | HTTPS only. Plain `http://` is accepted for `localhost`/loopback (tests). |
| `timeout` | `10 s` (`5 s` connect) | Seconds, or an `httpx.Timeout`. |
| `max_retries` | `0` | Opt-in retries (max 5). See [Rate limits](#rate-limits-and-retries). |
| `transport` | `None` | Test seam, e.g. `httpx.MockTransport`. |
| `http_client` | `None` | Your own `httpx.Client` / `httpx.AsyncClient`. It is never closed by the SDK, and its own timeout applies. |

| Method | Description |
| --- | --- |
| `get_latest_rates()` | Rolling last 24 hours, computed by the provider at request time. |
| `get_rates(date_from, date_to)` | Explicit window, strictly shorter than 24 hours. |
| `get_rates_for_day(day)` | `day 00:00:00` to `day 23:59:59`. One request. |
| `close()` / `aclose()` | Release connections. Idempotent. Also called by `with` / `async with`. |

Using a client after it was closed raises `ElToqueError`.

### `RatesResponse`

| Attribute | Description |
| --- | --- |
| `data` | The decoded JSON body, **exactly as the provider sent it** (object, list, scalar or `null`). |
| `rates` | Property: validated typed view, a `Rates` object (see below). Raises `ElToqueDecodeError` if the payload does not have the confirmed shape. |
| `status_code` | HTTP status (SDK metadata). |
| `rate_limit` | `RateLimitInfo` with optional `limit`, `remaining`, `reset`, `retry_after` (SDK metadata). |
| `received_at` | UTC timestamp of when the SDK received the response (SDK metadata). |

### `Rates`

| Attribute | Description |
| --- | --- |
| `rates` | Read-only mapping of provider code (e.g. `"USD"`, `"USDT_TRC20"`) to `Decimal`. Values are the provider's, never rounded or converted. The set of codes is open and can change. |
| `reported_at` | Naive `datetime` built from the response's `date`/`hour`/`minutes`/`seconds`. It is when the provider computed the answer, **not** the requested window; its time zone is undocumented (observed near UTC-4). |

`eltoque.ATTRIBUTION` holds the source notice to show next to rates.

### Exceptions

```text
ElToqueError
├── ElToqueConfigurationError   invalid token, base_url, timeout, retries
├── ElToqueValidationError      invalid arguments, detected before any request
├── ElToqueNetworkError         connection, DNS, TLS, protocol failures
├── ElToqueTimeoutError
├── ElToqueDecodeError          200 response that is not valid JSON, or too large
└── ElToqueAPIError             has .status_code, .body_excerpt, .rate_limit, .retry_after
    ├── ElToqueBadRequestError       400
    ├── ElToqueAuthenticationError   401
    ├── ElToqueUnprocessableError    422
    ├── ElToqueRateLimitError        429
    └── ElToqueServerError           5xx
```

Other 3xx/4xx statuses raise the base `ElToqueAPIError`. See [docs/errors.md](docs/errors.md).

## Date and time rules

- `date_from` and `date_to` must be **naive** `datetime` objects. Timezone-aware values are
  rejected, because the API does not document its time zone and the SDK will not guess one.
- They are sent as `YYYY-MM-DD HH:MM:SS` (microseconds are dropped).
- `date_from` must be earlier than `date_to`, and the window must be **shorter than 24 hours**,
  otherwise the API answers HTTP 400. The SDK rejects invalid windows before any request.
- `get_rates_for_day` is a convenience; it is not guaranteed to be a complete local calendar day.

## Rate limits and retries

By default each API key may make **60 requests/minute and up to 10 requests/second**; your key
may have different limits. Over the limit the API answers `429` with a `Retry-After` header.

- Retries are **off** (`max_retries=0`). Every retry consumes quota.
- With `max_retries > 0` the SDK retries only `429`, `502`, `503`, `504` and transport failures,
  never `400`, `401` or `422`.
- `Retry-After` is honored. If the server asks for longer than 30 s (or the 60 s total budget),
  the error is raised instead of waiting.
- There is no background polling, caching or bulk collection. You decide when to call.

## Known limitations

- Only one operation is documented by the provider: `GET /v1/trmi`. That is all this SDK calls.
- The provider **does not publish a schema** for a successful response. The `Rates` view follows
  what was observed on the live API (2026-10-23, see [docs/api-contract.md](docs/api-contract.md)),
  not a promise from elTOQUE: if the payload changes, `response.rates` raises
  `ElToqueDecodeError` while `response.data` keeps working.
- The time zone of the API is undocumented (see above).
- The API is more lenient than its documentation (for example it accepts a window of exactly 24 h
  and a single `date_from`); the SDK stays with the documented rules.
- Installing this SDK does not give you access to the API; you need your own approved token.

## Supported Python versions

Python 3.11, 3.12, 3.13 and 3.14. No framework is required.

## Development

```bash
uv sync                      # or: pip install -e . && pip install pytest pytest-asyncio pytest-cov ruff mypy build twine
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest                # offline, no token needed
uv run python -m build
uv run twine check dist/*
```

Optional live check, only with your own authorized token (never run in CI). One request; the
script prints the response shape, never provider values. See
[docs/live-testing.md](docs/live-testing.md):

```bash
ELTOQUE_API_TOKEN=... ELTOQUE_ALLOW_LIVE_TESTS=1 python scripts/live_check.py
```

## Security and legal

- Treat your token like a password. See [docs/security.md](docs/security.md).
- This project is not affiliated with elTOQUE. When you display rates, name **elTOQUE as the
  source** and describe them as **reference estimates**, as the
  [terms of use](https://eltoque.com/api-tasas-de-eltoque-terminos-y-condiciones-de-uso) require.
  Do not modify the data, share your key, resell the data or mass-extract it.
- The [MIT license](LICENSE) covers this SDK's source code only. It grants no rights over
  elTOQUE's API, data, name or trademarks.

## Official resources

- API landing page: <https://tasas.eltoque.com/>
- Interactive docs: <https://tasas.eltoque.com/docs/>
- OpenAPI document: <https://tasas.eltoque.com/static/swagger.json>
- What is and is not verified: [docs/api-contract.md](docs/api-contract.md)

## Community

- Contributing guide: [CONTRIBUTING.md](CONTRIBUTING.md)
- Code of conduct: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- Security policy: [SECURITY.md](SECURITY.md)
- Release notes: [CHANGELOG.md](CHANGELOG.md)
