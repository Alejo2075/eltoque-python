# Configuration

Both clients take the same keyword arguments. Nothing is read from the environment or from
`.env` files by the library: pass the token explicitly (typically from `os.environ`).

```python
import os

import httpx

from eltoque import ElToqueClient

client = ElToqueClient(
    api_token=os.environ["ELTOQUE_API_TOKEN"],
    timeout=httpx.Timeout(10.0, connect=5.0),
    max_retries=0,
)
client.close()
```

## Parameters

| Parameter | Default | Validation |
| --- | --- | --- |
| `api_token` | required | Non-empty, printable ASCII, no whitespace or control characters (blocks header injection). A `Bearer ` prefix is rejected. |
| `base_url` | `https://tasas.eltoque.com` | `https` required; `http` only for `localhost`, `127.0.0.1`, `::1`. No credentials, query or fragment. Trailing `/` is stripped. |
| `timeout` | `httpx.Timeout(10.0, connect=5.0)` | Positive finite number, or an `httpx.Timeout`. |
| `max_retries` | `0` | Integer from 0 to 5. |
| `transport` | `None` | `httpx.BaseTransport` (sync) / `httpx.AsyncBaseTransport` (async). Test seam. |
| `http_client` | `None` | An `httpx.Client` / `httpx.AsyncClient` you own. |

Invalid values raise `ElToqueConfigurationError`. Messages never contain the token.

## Injecting your own HTTP client

```python
import os

import httpx

from eltoque import ElToqueClient

with httpx.Client(timeout=30.0) as http:
    client = ElToqueClient(os.environ["ELTOQUE_API_TOKEN"], http_client=http)
    client.get_latest_rates()
    client.close()  # does not close `http`; you own it
```

Rules:

- The SDK **never closes** a client you inject; closing the SDK client only marks it unusable.
- The injected client's own timeout applies (`timeout=` is ignored).
- Redirects are never followed for SDK requests, even if your client enables them, so the
  `Authorization` header cannot be forwarded to another host.
- `http_client` and `transport` are mutually exclusive.

## Retries

Disabled by default. When enabled (`max_retries=1..5`):

| Situation | Behavior |
| --- | --- |
| 429 with `Retry-After` | Waits that long, if it is at most 30 s |
| 429 without `Retry-After`, 502, 503, 504, network error, timeout | Exponential backoff: 0.5 s, 1 s, 2 s, ... |
| 400, 401, 422, other 4xx, 500, invalid JSON | Never retried |
| Total waiting exceeds 60 s | Stops and raises the last error |

Every retry is a real request and consumes your quota. The async client waits with
`asyncio.sleep`, so task cancellation interrupts the wait immediately.

## Response size

Successful bodies larger than 5 MiB raise `ElToqueDecodeError` (the body is streamed and
checked, not loaded blindly).
