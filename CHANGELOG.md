# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project adheres to
[Semantic Versioning](https://semver.org/). Before 1.0, minor versions may contain breaking
changes; they will always be listed here. The SDK version is independent of the elTOQUE API
version (`1.0.beta`).

## [Unreleased]

### Documentation

- `docs/api-contract.md` now records the HTTP 200 shape, query behavior and a provider-side rate-limit
  anomaly observed against the live API on 2026-10-23 (shapes only; no values or tokens).

## [0.1.1] - 2026-10-23

### Added

- `scripts/live_check.py`: opt-in single-request check against the real API that prints only the
  response shape (never provider values), plus `docs/live-testing.md` with the validation
  checklist for the first authorized run.

### Changed

- README header now shows the project logo (absolute URL, so it also renders on PyPI) and
  documents `pip install eltoque-python`.

## [0.1.0] - 2026-10-22

First release. Unpublished until the repository owner approves it (see docs/publishing.md).

### Added

- `ElToqueClient` and `AsyncElToqueClient` for the documented `GET /v1/trmi` operation:
  `get_latest_rates()`, `get_rates(date_from, date_to)` and `get_rates_for_day(day)`.
- `RatesResponse` envelope that exposes the provider JSON untouched, plus `RateLimitInfo`
  parsed from `X-RateLimit-*` and `Retry-After` headers.
- Exception hierarchy rooted at `ElToqueError`, with one subclass per documented HTTP status.
- Strict validation: naive datetimes only, `date_from < date_to`, window shorter than 24 hours.
- Opt-in, bounded retries (`max_retries`, default 0) honoring `Retry-After`.
- Safety defaults: HTTPS-only base URL, redirects never followed, 5 MiB response cap, token
  redacted from `repr`, errors and logs.
- Injectable `httpx` client/transport with explicit ownership semantics.
- Offline test suite (`httpx.MockTransport`), opt-in live integration test, README and Spanish
  quickstart, configuration/errors/security guides, runnable examples.

### Known limitations

- The provider does not publish the HTTP 200 schema; `RatesResponse.data` is untyped.
- The provider's time zone is undocumented.
- Not yet verified against the real API (no authorized token was used).
