# CLAUDE.md — eltoque-python

> Engineering brief for Claude Code and human contributors.
> Last reviewed: 2026-10-22. API documentation can change; revalidate against the official sources before each release.
> **Mission:** Build a polished, lightweight, secure, independently maintained Python SDK for the official elTOQUE exchange-rate API. Package it for PyPI so any authorized Python application can install and use it.

## 0. Execution instructions for Claude

You are the lead Python library engineer on this repository. **Build the library and supporting repository files** rather than only writing an implementation plan.

1. Read this document entirely. Inspect the current repository before making changes. Preserve useful existing work.
2. Check the *official* API contract and Terms of Use in Section 2 whenever network access is available. Log noteworthy changes in `docs/api-contract.md`.
3. Do **not** make live authenticated API calls without a token that the repository owner deliberately supplies for that purpose. No token is needed for normal development, CI, or release packaging.
4. Never guess successful response JSON fields: the currently published OpenAPI file does **not** define the schema of HTTP 200. Ship a useful, honestly labeled generic response wrapper first, and add carefully typed financial fields only once their shape has been validated with permission.
5. Implement code, documentation, automated tests, formatting, type checks, reproducible packaging, and release workflows. Run verification commands and fix issues. Explain only what could not be verified.
6. Do not publish packages, create remote repositories, request API keys, register applications, or make changes to third-party accounts without the owner's explicit approval and credentials.
7. Treat downstream applications as responsible for their **own approved API registration and key**. Do not provide a shared proxy, bundled token, scraping fallback, credential generator, or bulk data harvesting function.
8. Favor clean and minimal over speculative functionality. One documented API endpoint does not justify a giant framework.

---

## 1. Product vision

**Project:** `eltoque-python` (working name; check final name availability on PyPI before publishing).

**Proposed PyPI distribution name:** `eltoque-python`.

**Proposed import package:** `eltoque` (verify that this import does not collide with another installed distribution).

**Tagline:** *A modern, typed Python client for the official elTOQUE exchange-rate API.*

**Positioning:** Independent, community-maintained SDK; not developed, sponsored, endorsed, or supported by elTOQUE.

**Scope:** Read-only access to the provider's published TRMI exchange-rate endpoint with well-designed sync/async Python interfaces, resilient HTTP handling, secure configuration, and packaging that just works.

**Primary users:** Python developers building authorized backends, scripts, data visualizations, and applications with the proper permission to display the rate data. No data aggregation, financial recommendations, resale, or republishing service.

**Design principles:**

- Zero framework lock-in: works in plain Python, Django, Flask, FastAPI, notebooks, AWS Lambda, etc.
- No secrets in source, docs, test fixtures, artifacts, HTTP logs, or Git history.
- Predictable exceptions, explicit timeouts, bounded retries, clear close semantics.
- Sync and async APIs with matching behavior.
- Preserve values accurately; do not silently alter data, round currencies, or claim rates are official.
- Future-proof compatibility with unknown JSON keys while provider's response schema is unverified.
- Excellent public developer experience, friendly README, meaningful examples, strong automated tests.
- Respect API terms and attribute elTOQUE as the source.

### Deliverables

A real repository ready for the owner to commit and share:

- Installable package, `pyproject.toml`, `src/` layout, sdist and wheel.
- `ElToqueClient` and `AsyncElToqueClient` with typed method signatures.
- Response wrapper and stable error types; comprehensive unit tests using offline HTTP mocks.
- Beautiful, accurate root `README.md`, plus `docs/`, `examples/` and a Spanish quickstart.
- `.github/workflows/ci.yml` and `.github/workflows/publish.yml` (PyPI Trusted Publishing, **not enabled by default for unsolicited publication**).
- `.gitignore`, `.editorconfig`, `LICENSE`, `CHANGELOG.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` (if appropriate), `SECURITY.md`, `.env.example` with fake placeholders only.
- Developer commands and release checklist. No actual PyPI publication until authorized.

---

## 2. Source of truth — official elTOQUE API

**Use these first and link to them in project documentation:**

- API landing page: https://tasas.eltoque.com/
- Interactive documentation: https://tasas.eltoque.com/docs/
- **OpenAPI v3 JSON**: https://tasas.eltoque.com/static/swagger.json
- API key application form: https://tasas-token.eltoque.com/
- Terms and conditions: https://eltoque.com/api-tasas-de-eltoque-terminos-y-condiciones-de-uso
- Provider's API announcement: https://eltoque.com/eltoque-abre-acceso-a-su-api-de-las-tasas-de-cambio
- Python packaging guide: https://packaging.python.org/en/latest/tutorials/packaging-projects/
- PyPI Trusted Publishing: https://docs.pypi.org/trusted-publishers/

### Verified contract as of 2026-10-22

| Item | Verified value / interpretation |
| --- | --- |
| API origin | `https://tasas.eltoque.com` |
| OpenAPI document | `3.0.0` |
| API info version | `1.0.beta` (this is **not** the SDK package version) |
| Publicly documented operation count | **1** |
| HTTP method and path | `GET /v1/trmi` |
| Operation ID | `trmiV1` |
| Purpose | Median exchange-rate figures based on offers in the Cuban informal market |
| Authentication | HTTP bearer scheme (`Authorization: Bearer <token>`), documented format JWT |
| `date_from` | Optional query parameter, example `2022-10-27 00:00:01` |
| `date_to` | Optional query parameter, example `2022-10-27 23:59:01` |
| No date parameters | Returns the rolling rates for the last 24 hours from request time |
| Explicit range | Must be **less than 24 hours**; longer intervals trigger HTTP 400 |
| Published success body | HTTP 200 documented **without a JSON schema** |
| Error statuses documented | 400, 401, 422, 429; handle 5xx and other unexpected statuses too |
| Default key limit | 60 requests/minute AND up to 10 requests/second; individual keys can differ |
| Rate-limit headers | `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` |
| 429 handling | `Retry-After` in seconds; JSON may include `error` and `limit` |

**Do not fabricate other operations.** In particular, there are no documented standalone `/latest`, `/historical`, `/convert`, `/currencies`, `/health`, `/auth`, `/rates` endpoints. Convenience Python methods can all call `GET /v1/trmi`.

### Query examples (documentation only; no real token)

```bash
# Most recent rolling 24-hour calculation
curl --fail-with-body \
  -H 'Authorization: Bearer YOUR_APPLICATION_TOKEN' \
  'https://tasas.eltoque.com/v1/trmi'

# Example date range: 23 hours 59 minutes 59 seconds
curl --fail-with-body -G \
  -H 'Authorization: Bearer YOUR_APPLICATION_TOKEN' \
  --data-urlencode 'date_from=2022-10-27 00:00:00' \
  --data-urlencode 'date_to=2022-10-27 23:59:59' \
  'https://tasas.eltoque.com/v1/trmi'
```

### Important unknowns — explicitly track them

The official OpenAPI document currently does **not** give a 200 payload example, response JSON structure, field names, currencies, units, precision, time-zone conventions, missing-data behavior, or stable pagination/streaming semantics. Therefore:

1. Create `docs/api-contract.md` with a verified/unverified checklist and source URLs.
2. Implement `RatesResponse` as a safe envelope around the **unchanged decoded JSON payload** (e.g. `data: Any` with documented `raw` or `data` access; do not claim `USD`, `EUR`, `MLC`, `timestamp`, etc. are guaranteed keys).
3. Mark any typed currency-specific model as **pending confirmation**, not stable functionality. If tests need examples, use **explicitly synthetic fixtures** representing valid JSON shapes rather than masquerading as actual elTOQUE payloads.
4. When authorized test credentials become available, inspect sanitized HTTP 200 responses (never store tokens, identifying information, or restricted real datasets in Git) and record the discovered schema and validation date.
5. Only then consider `Decimal`-preserving typed models; never silently coerce real financial data through floating-point rounding or rewrite provider values.
6. If reliable JSON is not returned, raise a meaningful decoding error; never silently treat malformed responses as `{}`.
7. Do not generate a typed client blindly from OpenAPI, because the response schema is incomplete.

### Date/time behavior

- Use a clear public date-time contract with explicit validation.
- Safest v0.1 choice: accept **naive `datetime` values**, format exactly as documented `YYYY-MM-DD HH:MM:SS`, and document that the upstream timezone is **not specified**. Never assume UTC or Cuba time.
- Reject timezone-aware values until an explicit timezone conversion contract has been confirmed (or require the caller to intentionally normalize first).
- Require `date_from < date_to` and `(date_to - date_from) < timedelta(hours=24)` for explicit ranges; reject invalid values before HTTP.
- If only one bound is given, reject unless the provider behavior has been verified and deliberately documented.
- Provide `get_rates_for_day(day: date)` as an optional convenience: format `00:00:00` through `23:59:59` of that date, documenting the provider-timezone ambiguity; never claim a guaranteed complete local-calendar-day result.
- Avoid doing multiple back-to-back requests to assemble longer historical periods; such bulk collection can violate the API terms unless specifically authorized.

### Source attribution and terms — mandatory

The owner of the API says each application must be registered for its own access key; permission is limited, revocable, nontransferable, and nonsublicensable. Among other things, terms require naming elTOQUE as the source and describing the rates as reference estimates, not official rates. They prohibit sharing API keys, mass extraction, unapproved data uses, modifying values, and reselling or sublicensing the data.

Implementation rules:

- This repository distributes **client code**, not credentials or provider data.
- Never hardcode or publish a token, use your token to service all SDK consumers, or promise the library grants API access.
- Never implement token generation, automatic application registration, scraping, web-page parsing as fallback, or covert scraping.
- Never build a public redistributing proxy, scraping pipeline, bulk historical mirror, or automated downloader.
- No default/background API polling; all requests are initiated by the consumer. No implicit multi-day loops.
- Store no real rate data in releases, fixtures, GitHub pages, or README screenshots unless permission is established.
- README, package docs, and examples must prominently state: **"Exchange rates are indicative, not official. Source: elTOQUE. Access requires registration and an application-specific API token."**
- Put an independent/unofficial disclaimer prominently near project name; do not copy protected logos or suggest endorsement.
- The MIT license can cover **our own code only**. It does **not** grant rights over elTOQUE's trademarks, API, or data. If you include an MIT license, don't copy code from other repos without license review.
- If the Terms of Use or approval conditions prohibit a proposed integration pattern, remove it or get written authorization rather than engineering around restrictions.

---

## 3. Python stack & dependency policy

**Target minimum Python: 3.11** (modern and practical for a new open-source library). Test on compatible newer CPython releases (3.12, 3.13, 3.14 where the dependency ecosystem supports it). Use standard-library idioms and avoid requiring system-native extensions.

| Area | Selected approach | Why |
| --- | --- | --- |
| Packaging | `pyproject.toml` + Hatchling | PEP 517/518 build, small and straightforward |
| Source layout | `src/eltoque/` | Prevent import-from-working-directory mistakes |
| HTTP | `httpx` | Single library with pooled synchronous and asynchronous clients |
| Config | Python dataclass + explicit constructor args | No heavyweight settings framework |
| JSON | HTTPX JSON decode / Python stdlib | Avoid extra required runtime dependency |
| Models | `dataclasses`, `typing`, `Decimal` once verified | Keep JSON reliable and typed API incremental |
| Errors | Public `ElToqueError` exception family | Predictable error handling |
| Tests | `pytest` + `httpx.MockTransport` + `pytest-cov` | Offline, repeatable test suite |
| Lint / format | Ruff | Single formatter/linter |
| Type checking | mypy (or an equivalent chosen deliberately) | Catch public typing defects |
| CI | GitHub Actions | Cross-version quality gates |
| Package build | `python -m build` | Produce wheel + sdist |
| Artifact check | `python -m twine check dist/*` | Validate package metadata/README renderability |
| Publication | PyPI + GitHub Actions OIDC Trusted Publishing | Avoid long-lived PyPI credentials |
| Docs | Strong `README.md` + Markdown docs | Easy to maintain at this project size |

Choose up-to-date mutually compatible releases **at implementation time**, and use bounded declared runtime dependencies (avoid unreviewed exact runtime pins). Dev dependency locking is acceptable for reproducible CI. Do not invent version numbers or choose dependencies merely to seem current.

Do **not** require FastAPI, Django, Pandas, NumPy, Pydantic, Celery, Redis, requests, cryptography, or httpx HTTP/2 extras in the base SDK without a concrete need. Keep the wheel small and pure Python.

### Packaging and versioning

- Start with SDK version `0.1.0`, independent of API `1.0.beta`.
- Recommended `requires-python = ">=3.11"`.
- Use PEP 621 metadata: name, version/dynamic version, description, readme, license expression if supported, authors, classifiers, `requires-python`, dependencies, keywords, project URLs.
- Provide type marker `src/eltoque/py.typed` (PEP 561).
- Write `__init__.py` public exports carefully; avoid exporting internal implementation classes.
- Follow Semantic Versioning, or document the realistic pre-1.0 compatibility policy. Keep changelog.
- Do not claim the PyPI project name is reserved; confirm availability before publishing.
- Include wheel and sdist metadata, README and LICENSE; test installation of built wheel in a **fresh** virtual environment and importing from outside the repo root.

---

## 4. Required public API and sample user experience

The following is a **proposed SDK interface**; it is not a description of an already existing package. Implement and document it consistently. The returned response's provider fields stay unverified.

### Synchronous example

```python
import os
from eltoque import ElToqueClient

with ElToqueClient(api_token=os.environ["ELTOQUE_API_TOKEN"]) as client:
    response = client.get_latest_rates()
    print(response.data)  # Original decoded provider JSON; schema not yet verified
```

### Historical interval example

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

### Async example

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

### Developer-facing behavior

- `ElToqueClient(api_token: str, *, timeout: float | httpx.Timeout = ..., max_retries: int = 0, ...)`.
- `AsyncElToqueClient` provides matching async methods and semantics.
- `get_latest_rates() -> RatesResponse` (sync or `await` async).
- `get_rates(date_from: datetime, date_to: datetime) -> RatesResponse` (sync or async).
- Optional `get_rates_for_day(date)` helper if semantics can be clearly documented.
- Optional `base_url` for test injection only, with sensible validation and no unsafe redirects; default official HTTPS origin.
- Permit injected `httpx.Client` / `httpx.AsyncClient` or transport via a documented test seam, with explicit ownership semantics (never close caller-owned clients unexpectedly).
- Support `with` / `async with`, explicit `close()` / `aclose()`, and clear error if used after closing.
- `RatesResponse.data` returns decoded API JSON as-is; optional `status_code`, `rate_limit`, `received_at` are **SDK metadata**, not invented provider fields.
- Accept only nonempty tokens, reject whitespace/control characters to prevent HTTP header injection. Never print or repr the raw token.
- All examples must work exactly with public exports and real signatures; add doctests or test the snippets.

### Rate limit information (optional metadata)

If exposing this, parse safely into an SDK-owned object `RateLimitInfo` containing `limit`, `remaining`, `reset` and `retry_after` as optional values. Malformed/missing header values must not crash otherwise successful API requests.

### Exception hierarchy

```text
ElToqueError
├── ElToqueConfigurationError
├── ElToqueValidationError
├── ElToqueNetworkError
├── ElToqueTimeoutError
├── ElToqueDecodeError
└── ElToqueAPIError
    ├── ElToqueBadRequestError       # 400
    ├── ElToqueAuthenticationError   # 401
    ├── ElToqueUnprocessableError    # 422
    ├── ElToqueRateLimitError        # 429
    └── ElToqueServerError           # 5xx
```

- Preserve HTTP status, safe response excerpt, retry metadata, and a meaningful human-readable message without leaking secrets.
- For other unexpected 4xx/3xx statuses, use general `ElToqueAPIError` and do not silently follow cross-host redirects that could leak bearer credentials.
- Retry only safe GET requests if configured. Respect the provider's 429 `Retry-After`; cap attempt count, total delay, and individual timeouts. Document that retries consume quota and default to `max_retries=0`.
- Never retry 400/401/422; optionally retry known transient 5xx and transport failures within strict limits.
- Avoid blocking `time.sleep()` in async code; use `asyncio.sleep()`.
- No unbounded concurrency, background refresh, or automatic data harvesting.

---

## 5. Suggested repository layout

```text
eltoque-python/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml
│   │   └── publish.yml
│   ├── ISSUE_TEMPLATE/
│   └── pull_request_template.md
├── docs/
│   ├── api-contract.md
│   ├── quickstart.es.md
│   ├── configuration.md
│   ├── errors.md
│   ├── security.md
│   └── publishing.md
├── examples/
│   ├── basic.py
│   ├── async_basic.py
│   ├── date_range.py
│   └── fastapi_integration.py       # optional, not runtime dependency
├── src/
│   └── eltoque/
│       ├── __init__.py
│       ├── _client.py
│       ├── _async_client.py
│       ├── _transport.py            # shared helpers if useful
│       ├── _dates.py
│       ├── _config.py
│       ├── _version.py              # only if needed by build strategy
│       ├── exceptions.py
│       ├── models.py
│       └── py.typed
├── tests/
│   ├── conftest.py
│   ├── fixtures/                    # synthetic only; no provider data
│   ├── test_client.py
│   ├── test_async_client.py
│   ├── test_dates.py
│   ├── test_errors.py
│   ├── test_rate_limits.py
│   ├── test_transport.py
│   └── test_public_api.py
├── .env.example
├── .gitignore
├── .editorconfig
├── .pre-commit-config.yaml          # optional
├── CHANGELOG.md
├── CLAUDE.md
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── LICENSE
├── README.md
├── SECURITY.md
├── pyproject.toml
└── uv.lock                           # only if choosing uv for dev workflows
```

Avoid duplicate module structures, speculative webhooks, or excessive abstractions. Private implementation helpers get leading underscores; only documented surfaces become stable public API.

---

## 6. README.md — must look excellent

Write a professional, visually polished, **accurate and accessible** GitHub README aimed at international Python developers. Main README **in English**, with a link to `docs/quickstart.es.md` for Spanish readers. Keep examples executable and credentials obviously fake.

Recommended README sequence:

1. **Clean title + one-sentence product pitch**: `eltoque-python` and *Unofficial Python SDK for elTOQUE exchange-rate data*.
2. **Badges**: Python compatibility, CI status, PyPI version, PyPI downloads (optional, only if reliable), license. Use real URLs after the GitHub owner/name and PyPI distribution are confirmed. Before that, omit unavailable badges rather than showing broken placeholders.
3. **Prominent unofficial disclaimer** and clear source attribution; rates are **reference estimates**, not official exchange rates.
4. **Why use it?** Concise features: sync + async, typed Python interface, timeouts, errors, rate-limit handling, pure Python, tested with mocks.
5. **Installation**: `pip install eltoque-python` **only after publication**. Before publication label it as planned; give honest local installation instructions (`pip install -e .`) now.
6. **Get your API token**: Link to the official registration form; explain that each consuming application needs its own approved key, and never show a real token.
7. **Quickstart**: small, correct sync example referencing `ELTOQUE_API_TOKEN` env var. Add async version and date window example.
8. **API reference**: methods, parameters, return object, exceptions; include a brief table.
9. **Date/time rules**, 24-hour limit, and unknown upstream timezone.
10. **Rate limits and error handling**: 60/minute and 10/second defaults *subject to key-specific limits*; `Retry-After` on 429; retries opt-in.
11. **Known limitations**: only one official documented operation; response schema not published; typed rate fields unverified until validated; no guaranteed access with SDK installation.
12. **Supported Python versions** and framework independence.
13. **Development**: install, test, lint, type check, build, contributing.
14. **Publishing / release**: PyPI link only after genuinely published.
15. **Security + legal**: don't expose tokens, no affiliation, link to elTOQUE terms, project's MIT license applies only to SDK code.
16. **Community**: issues, PRs, contribution guide and changelog; links only when they exist.

README visual style:

- Attractive typography using Markdown headings, concise paragraphs, judicious tables, and small code blocks.
- A tasteful project logo/banner **only if created and owned**; do not pull elTOQUE logos or claim official visual affiliation.
- Avoid excessive emojis, giant banners, marketing exaggerations, fabricated installs/stars/downloads, screenshots, badges, endorsements, or fake releases.
- Include one easily readable short example above the fold.
- All links should lead to actual docs, official sites, or already created repo files.
- Check README renders as PyPI long description (`twine check`).
- README code examples must match the actual implementation and be exercised in tests where feasible.

A separate Spanish guide should give install instructions, authenticating, synchronous/asynchronous calls, handling dates, 429 responses, and the unofficial attribution/legal note.

---

## 7. Testing — must be useful without any token

**No real API key needed for standard test suite.** Use `httpx.MockTransport` or an equivalent deterministic HTTP mock.

Minimum behavioral test matrix:

- Correct HTTP path, query parameters, bearer header, timeouts, and HTTPS base URL.
- No date params = latest request; explicit date range encoding, order, format, and rejection of equal/reversed/>=24h windows.
- Handling naive and aware datetimes exactly as documented; no timezone guess.
- JSON list/object/scalar/null responses: preserve decoding truthfully, and reject malformed JSON; be intentional about supported payload types.
- Missing/empty/invalid token and header injection attempts rejected.
- HTTP 200 with missing rate headers; integer and malformed rate headers.
- 400/401/422/429/5xx and generic unexpected status mapping.
- 429 `Retry-After` and retries: disabled by default, bounded when enabled, cancellation-safe async delays.
- Connection errors, DNS errors, connect/read timeouts, unexpectedly closed clients.
- Credentials never appear in exception messages, `repr`, logs, test snapshots, README examples, or recorded mock requests shown in output.
- Sync + async parity including context manager lifecycle, injected client ownership, no connections after close.
- Proxy redirects: ensure Authorization does not leak to unintended hosts.
- Simulated concurrency under rate limits; no automatic polling.
- Integration tests are optional, **explicit opt-in**, skipped unless `ELTOQUE_API_TOKEN` exists and the owner authorizes tests for that registered application; never run in public CI by default.
- Build the wheel/sdist and install from generated wheel inside isolated environment; verify imports and package metadata.

Set an appropriately high coverage target on meaningful library logic (aim ~90%+, not by excluding difficult branches). Type-check and lint public APIs. Tests must not require Internet access or mutate third-party data.

---

## 8. CI/CD & publishing to PyPI

### GitHub Actions: ci.yml

- Triggers: pull requests, pushes to main, and manual dispatch as useful.
- Matrix for Python 3.11, 3.12, 3.13 and 3.14 when supported by selected packages.
- Install project and dev dependencies deterministically.
- Run `ruff check`, `ruff format --check`, `mypy`, `pytest`, `python -m build`, `twine check dist/*`.
- On at least one job, install built wheel in a fresh venv and run an import/quickstart smoke test with mocks (not the real API).
- CI has no token of elTOQUE. Job permissions default least privilege (`contents: read`).
- Use supported stable GitHub Actions and pin third-party action commits where practical; keep Dependabot or equivalent update process.

### GitHub Actions: publish.yml

- Add a **manual approval gate** or explicit release tag (`v*`) + protected GitHub environment `pypi`; no uploading on PR or ordinary push.
- Build and validate distribution first. Publish using PyPA `pypa/gh-action-pypi-publish` with **PyPI Trusted Publishing (OIDC)**, `id-token: write` **only** for the publish job. No stored long-lived PyPI token.
- Document configuring the exact PyPI trusted publisher owner/repo/workflow/environment and verifying project name ownership.
- Support a separate manually gated TestPyPI step if desirable; do not assume it is already configured.
- Do not assert a successful publish unless the remote registry confirms it.
- Git tag, package metadata version, docs, and changelog must agree.
- Never auto-create accounts, accept licenses, register a domain, or publish a release on behalf of the owner.

### Local release checks

```bash
python -m pip install -e '.[dev]'
ruff check .
ruff format --check .
mypy src
pytest -q
python -m build
python -m twine check dist/*
```

Only use the `[dev]` install extra if defined in the actual `pyproject.toml` (otherwise document an alternative development dependency workflow). Confirm built wheel contains `py.typed`, LICENSE, relevant metadata and the import package.

### Metadata placeholders that must be resolved before release

- Actual package/repository name and GitHub owner.
- Maintainer name/contact that owner wants public; do not infer or expose private emails.
- Confirmed license for code authored in this project (MIT recommended).
- Chosen PyPI name not already reserved by someone else.
- Real CI badge URLs only after CI exists.
- PyPI account and trusted publisher registration: **manual user action**.
- Official elTOQUE API access remains a **separate** registration, unrelated to PyPI publication.

---

## 9. Security standards and code quality

- Token provided explicitly or via application-side environment variable; do not auto-read local `.env` files in the library or request a token interactively.
- All network traffic over validated HTTPS by default; any HTTP base URL override must be clearly limited to local tests, never silently accepted in production.
- Disable or safely control redirects from provider host to a different host; don't forward Authorization to an unexpected domain.
- Bound response sizes where practical. No infinite retries, hangs, resource leaks, or secret-bearing debug output.
- Avoid printing full response bodies in exceptions by default; provider bodies may contain private info. Redact tokens and sensitive headers.
- Use `typing` throughout, clear docstrings, straightforward dataclasses / response types, narrow public exports.
- Ensure async code does not block the event loop. No global mutable token/session state.
- Handle JSON decode and HTTP error precedence consistently; do not turn all failures into generic ValueError.
- Do not alter provider rate values or compute conversions unless documented and explicitly requested; preserving raw data is safer while response schema is unknown.
- Provide secure defaults; configuration overrides must be explicit.
- If repository includes any demo web app, never use a private server token from a browser bundle.
- Supply a security contact procedure without publishing private information.

---

## 10. Development roadmap (deliver code, not just TODOs)

### Milestone A — working `0.1.0` (required now)

1. Create `pyproject.toml`, `src/eltoque`, package exports, typing marker.
2. Build sync/async clients around the verified GET endpoint.
3. Implement parameter validation, bearer auth, timeout, safe error hierarchy, accurate JSON response wrapper.
4. Implement injection/test seams, context managers, strict close behavior.
5. Add full offline test suite and CI; ensure builds install successfully in an isolated environment.
6. Write beautiful README, Spanish quickstart, security and API contract limitations, license/contribution/release docs.
7. Add guarded PyPI publication workflow, but don't publish or claim it is published.

### Milestone B — after authorized verification of real response (future)

1. With *explicit* owner authorization and their approved application token, make the smallest reasonable number of requests to verify the HTTP 200 schema.
2. Document verified example **with secret and copyrighted/restricted data removed**; don't commit real market data without permission.
3. Add typed `Decimal`-safe rate models *only for confirmed fields*, preserving an escape hatch for unknown keys.
4. Update tests and examples; only then advertise typed rates in README.
5. If provider terms permit, evaluate a minimal optional caching adapter; keep it opt-in and not a redistributing store.

### Milestone C — release readiness

1. Decide repository organization, PyPI package name, author and license.
2. Verify elTOQUE's current API terms and that the intended client distribution is consistent with them.
3. Run full tests/build/install/README checks; update changelog and tagged version.
4. Configure PyPI Trusted Publisher manually with the owner.
5. Publish only after explicit instruction and successful protected release checks.

---

## 11. Definition of done / acceptance checklist

- [ ] New user can clone repo, run editable install and tests without API credentials.
- [ ] Public sync and async code examples match real runnable SDK APIs.
- [ ] One official endpoint implemented; no invented routes or unapproved scraping.
- [ ] No assumption about the currently undocumented 200 response schema.
- [ ] Date validation guarantees explicit ranges <24 hours and documents unresolved timezone semantics.
- [ ] All HTTP errors and 429 headers have well-tested behavior.
- [ ] Safe credentials handling; zero secrets in repo and test output.
- [ ] Tests run entirely offline in CI and cover both client variants.
- [ ] Type checking, linting, formatting, package build, Twine checks succeed.
- [ ] Fresh-environment wheel installation works; import package and types are included.
- [ ] Root README is attractive, accurate, English-first, has a Spanish guide, and credits elTOQUE.
- [ ] Security, licensing, contribution, changelog, and policy documents exist.
- [ ] PyPI Trusted Publishing workflow is prepared with protected release gating.
- [ ] No account creation, token application, live API usage, or PyPI upload occurred without explicit permission.
- [ ] Documentation clearly separates **unofficial library license** from provider's **API access/data rights**.

---

## 12. Final Claude Code response format

When implementation is complete, report:

1. Files added or changed and why.
2. Implemented features and precise unsupported/unknown behaviors.
3. Command results for tests, linter, formatter, type checker, build, Twine check, and isolated wheel install.
4. Anything not verified due to absence of an authorized elTOQUE token, incomplete upstream success schema, or external account access.
5. Concise manual release prerequisites (confirmed PyPI name, public maintainer metadata, Trusted Publisher, user approval).
6. No claim of production certification, official endorsement, API approval, or PyPI publication without evidence.

**Final reminder:** This is a self-contained, independently maintained Python SDK for a narrowly documented external API. Engineer the library to be excellent without inventing functionality, misusing data, or requiring credentials for ordinary development.
