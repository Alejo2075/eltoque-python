# Contributing

Thanks for helping! This is a small, deliberately minimal SDK for a narrowly documented API.
Please read this page and the [Code of Conduct](CODE_OF_CONDUCT.md) first.

## Ground rules

- **Only documented behavior.** The official OpenAPI document defines one operation,
  `GET /v1/trmi`. Do not add endpoints, scraping, fallbacks, proxies, bulk downloaders,
  background polling or caching layers. See [docs/api-contract.md](docs/api-contract.md).
- **Never guess the response schema.** Typed rate fields are accepted only with a sanitized,
  permission-cleared sample validated against an authorized token.
- **No secrets, no provider data.** Never commit tokens, real responses or screenshots of real
  rates. Test fixtures must be explicitly synthetic.
- Keep it small: favor clean and minimal over speculative functionality.

## Setup

```bash
git clone <your fork>
cd eltoque-python
uv sync          # creates .venv with all dev tools (no token needed)
```

## Checks (all must pass)

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest                 # offline; coverage must stay >= 90%
uv run python -m build && uv run twine check dist/*
```

Tests use `httpx.MockTransport`; they must not touch the Internet. Live tests are opt-in
(`pytest -m integration`, needs `ELTOQUE_API_TOKEN` and `ELTOQUE_ALLOW_LIVE_TESTS=1`) and never
run in CI.

Every behavior change needs tests for **both** the sync and async clients, and README or guide
code blocks are executed by `tests/test_docs.py`, so keep them runnable.

## Commits

[Conventional Commits](https://www.conventionalcommits.org/): `type(scope): imperative summary`
(72 characters or fewer), body explaining *why* when it is not obvious.

| Type | Use |
| --- | --- |
| `feat` | New public functionality |
| `fix` | Bug fix |
| `refactor` | Internal change, same behavior |
| `test` | Tests only |
| `docs` | Documentation and examples |
| `build` | Packaging, dependencies |
| `ci` | GitHub Actions |
| `chore` | Repository upkeep |

Scopes: `repo`, `build`, `config`, `errors`, `dates`, `models`, `transport`, `retry`, `client`,
`async`, `api`, `examples`, `readme`, `docs`, `ci`, `release`.

Keep commits atomic: each one should leave all checks green, with code and its tests together.
Update `CHANGELOG.md` (`Unreleased`) for user-visible changes.

## Pull requests

1. Branch from `main` (`feat/...`, `fix/...`, `docs/...`).
2. Rebase rather than merge `main` into your branch; we keep a linear history.
3. Fill in the PR template and make sure the checks above pass.

## Security issues

Do not open a public issue. See [SECURITY.md](SECURITY.md).
