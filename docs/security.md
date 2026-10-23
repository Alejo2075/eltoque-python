# Security

## Your token

- Each application needs its own token, requested from elTOQUE. Do not share it, publish it, or
  embed it in code that runs in a browser or mobile app.
- Load it from the environment or a secrets manager and pass it explicitly. The library never
  reads `.env` files and never prompts for a token.
- Rotate it with elTOQUE if it may have leaked.

## What the SDK does to protect it

| Risk | Mitigation |
| --- | --- |
| Header injection | Tokens with whitespace, control or non-ASCII characters are rejected at construction. |
| Leaking in logs/errors | The token is absent from `repr`, exception messages, `body_excerpt` (redacted), logs and chained tracebacks. Covered by `tests/test_security.py`. |
| Sending it over plain HTTP | `base_url` must be `https`; `http` only for loopback hosts (tests). |
| Redirect to another host | Redirects are never followed, even with an injected client that enables them. A 3xx raises `ElToqueAPIError`. |
| Huge responses | Bodies over 5 MiB are rejected while streaming. |
| Runaway retries | Opt-in, at most 5, bounded delay (30 s each, 60 s total). |
| Shared state | No global token or session; each client owns its configuration. |

## What it does not do

- It does not validate TLS differently from `httpx` (certificates are verified by default).
- It cannot stop you from printing `response.data` or the token yourself.
- It does not bundle a token, proxy, mirror or fallback source, and never will.

## Reporting a vulnerability

Please do not open a public issue for security problems. Use the repository's private
vulnerability reporting (GitHub Security Advisories) once the repository is public.

## Terms of use

Using the API is subject to elTOQUE's
[terms](https://eltoque.com/api-tasas-de-eltoque-terminos-y-condiciones-de-uso): name elTOQUE as
the source, present rates as references, do not modify the data, do not share your key.
