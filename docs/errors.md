# Errors

Every exception raised by the SDK derives from `ElToqueError`.

| Exception | When | Retried when `max_retries > 0` |
| --- | --- | --- |
| `ElToqueConfigurationError` | Bad token, `base_url`, timeout, retries, or both `http_client` and `transport` | no (raised at construction) |
| `ElToqueValidationError` | Naive-datetime, ordering or 24-hour rule broken; non-`date` passed to `get_rates_for_day` | no (no request is made) |
| `ElToqueNetworkError` | Connection, DNS, TLS, protocol or mid-body read failure | yes |
| `ElToqueTimeoutError` | Connect, read, write or pool timeout | yes |
| `ElToqueDecodeError` | 2xx body is empty, not JSON, or larger than 5 MiB; also raised by `response.rates` when the payload does not match the confirmed shape | no |
| `ElToqueBadRequestError` | HTTP 400, e.g. interval of 24 hours or more | no |
| `ElToqueAuthenticationError` | HTTP 401: token wrong or expired | no |
| `ElToqueUnprocessableError` | HTTP 422: check the token | no |
| `ElToqueRateLimitError` | HTTP 429 | yes, honoring `Retry-After` |
| `ElToqueServerError` | HTTP 5xx | only 502, 503, 504 |
| `ElToqueAPIError` | Any other unexpected status (3xx, 403, 404, ...) | no |

## API error attributes

`ElToqueAPIError` and its subclasses expose:

- `status_code`: the HTTP status.
- `rate_limit`: a `RateLimitInfo` (`limit`, `remaining`, `reset`, `retry_after`; each may be `None`).
- `retry_after`: seconds from the `Retry-After` header, or `None`.
- `body_excerpt`: at most 200 characters of the response body, single-line, with the token
  redacted, or `None`. For diagnostics only: it is provider-controlled text.

`str(error)` is a fixed, safe sentence such as `HTTP 429: rate limit exceeded`; it never includes
the response body, URL query or token.

## About exception chaining

Transport failures (`ElToqueNetworkError`, `ElToqueTimeoutError`) are raised `from None`. The
message keeps the underlying exception type name (e.g. `ConnectError`) but drops the original
text, because a custom transport could put arbitrary content, even credentials, in it.

## Pattern

```python
import os

from eltoque import (
    ElToqueAuthenticationError,
    ElToqueClient,
    ElToqueError,
    ElToqueRateLimitError,
)

with ElToqueClient(os.environ["ELTOQUE_API_TOKEN"]) as client:
    try:
        rates = client.get_latest_rates()
    except ElToqueAuthenticationError:
        print("Check or renew your application token")
    except ElToqueRateLimitError as error:
        print("Wait", error.retry_after, "seconds")
    except ElToqueError as error:
        print("Unexpected failure:", error)
    else:
        print(rates.data)
```
