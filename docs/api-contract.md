# elTOQUE API contract

Last validated against the official sources: **2026-10-22** (no token used; only the public
OpenAPI document was fetched).

## Sources

- Landing page: <https://tasas.eltoque.com/>
- Interactive docs: <https://tasas.eltoque.com/docs/>
- OpenAPI JSON: <https://tasas.eltoque.com/static/swagger.json>
- API key form: <https://tasas-token.eltoque.com/>
- Terms of use: <https://eltoque.com/api-tasas-de-eltoque-terminos-y-condiciones-de-uso>

## Verified (from the published OpenAPI document)

| Item | Value |
| --- | --- |
| Origin | `https://tasas.eltoque.com` |
| OpenAPI / API version | `3.0.0` / `1.0.beta` (not the SDK version) |
| Operations | 1: `GET /v1/trmi` (`trmiV1`) |
| Auth | HTTP bearer (`Authorization: Bearer <token>`), JWT |
| Query | `date_from`, `date_to`, optional, example `2022-10-27 00:00:01` |
| No dates | Rolling last 24 hours from request time |
| Explicit range | Must be less than 24 hours, otherwise HTTP 400 |
| Documented errors | 400, 401, 422, 429 |
| Default limits | 60 requests/minute and 10 requests/second, per API key |
| Rate-limit headers | `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` on all responses |
| 429 | `Retry-After` (seconds) and JSON `{"error": "...", "limit": "60 per 1 minute"}` |

Terms highlights: name elTOQUE as the source, rates are referential, do not share your key,
do not modify the data (except to update it), one token per integrated application.

## Validated against the live API (2026-10-23)

Observed with one approved application token (one key, one day, a few dozen requests). Only the
*shape* is recorded; no rate values or tokens are stored in this repository.

### HTTP 200 body

```text
{
  "date":    str   (10 chars, e.g. "YYYY-MM-DD"),
  "hour":    int,
  "minutes": int,
  "seconds": int,
  "tasas":   { "<CODE>": float, ... }
}
```

- `tasas` maps a currency/asset code to a JSON number with 1 or 2 decimal places
  (observed codes in the latest response: `BTC`, `ECU`, `MLC`, `TRX`, `USD`, `USDT_TRC20`; a 2022
  window additionally returned `BNB`). The set of codes is **not fixed**: treat it as open.
- `date`/`hour`/`minutes`/`seconds` is a timestamp that advanced with each request, so it looks
  like the moment the answer was computed, **not** the requested window (a request for a 2022
  window still reported 2026-10-23).
- Time zone: that timestamp was about UTC-4 (Cuba summer time) and about 6 minutes ahead of an
  independent clock, so either the provider's clock is skewed or its fields are not plain local
  time. Whether `date_from`/`date_to` are read in that zone was **not** established.
- Historical windows are honored: a window in 2022 returned a different set of codes than the
  latest request.

### Query behavior (differs from, or goes beyond, the OpenAPI text)

| Request | Result |
| --- | --- |
| No dates | 200 |
| 2-hour window | 200 |
| Window of exactly 24 h | **200** (docs say longer than 24 h is an error; the SDK still rejects >= 24 h) |
| Only `date_from` | **200** |
| Only `date_to` | **400**, message "El intervalo de tiempo debe ser menor a 24 horas" |
| `date_from` later than `date_to` | **200** (the SDK rejects it before sending) |
| Window of 24 h + 1 s, 48 h | not verified (rate limited, see below) |

The SDK stays deliberately stricter than the API (naive datetimes, both bounds, `date_from <
date_to`, window shorter than 24 h) because those rules are the documented contract.

### Rate limiting

- This key reported `X-RateLimit-Limit: 10` and the 429 body said `"10 per 1 second"`, not the
  documented 60 per minute default: limits are per key.
- `X-RateLimit-Reset` is an epoch timestamp (seconds).
- **Provider-side anomaly:** after a burst of about 20 requests, the key stayed in HTTP 429 for
  several minutes even though requests were spaced 6 s apart. During that time `Retry-After`
  was **negative** (e.g. `-131`, decreasing), `X-RateLimit-Remaining` stayed at `10` and
  `X-RateLimit-Reset` stayed frozen in the past. This is consistent with a clock skew on the
  provider's side. The SDK ignores negative `Retry-After` values (`RateLimitInfo.retry_after` is
  `None`) and, with retries enabled, falls back to its own bounded backoff.
- Practical advice: keep well under the limit, avoid bursts, and do not hammer a 429.

## Still unverified

- [ ] Exact meaning and time zone of `date_from` / `date_to`.
- [ ] Behavior for windows slightly over 24 h and for future windows.
- [ ] Whether the set of currency codes and the number of decimals are stable.
- [ ] Behavior when no data exists for a window.
- [ ] Whether the provider's clock skew and the stuck 429 state are persistent.

Consequence: `RatesResponse.data` is returned untouched, and `RatesResponse.rates` (class `Rates`)
is a strictly validated `Decimal` view of the confirmed fields (`tasas` and the timestamp). It
raises `ElToqueDecodeError` on any mismatch rather than guessing.

## Change log of the contract

| Date | Change |
| --- | --- |
| 2026-10-22 | Initial validation; matches `CLAUDE.md` section 2. |
| 2026-10-23 | First live validation with an approved token: 200 shape, query behavior, rate-limit anomaly. |
