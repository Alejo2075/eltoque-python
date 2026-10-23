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

## Unverified / unknown

- [ ] Schema of the HTTP 200 body (the OpenAPI document defines none).
- [ ] Currencies, field names, units, precision.
- [ ] Time zone of `date_from` / `date_to` and of returned timestamps.
- [ ] Behaviour when only one of `date_from` / `date_to` is sent.
- [ ] Behaviour of missing data for a requested window.
- [ ] Exact semantics of `X-RateLimit-Reset` (epoch vs. seconds remaining).

Consequence: `RatesResponse.data` returns the decoded JSON untouched. Typed rate models are
deferred until the 200 schema is validated with an authorized token (Milestone B).

## Change log of the contract

| Date | Change |
| --- | --- |
| 2026-10-22 | Initial validation; matches `CLAUDE.md` section 2. |
