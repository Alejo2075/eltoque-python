## What and why

<!-- Short description and motivation. Link the issue if there is one. -->

## Checklist

- [ ] `ruff format --check .`, `ruff check .`, `mypy src` and `pytest` pass locally
- [ ] Tests cover both the sync and async clients (when behavior changed)
- [ ] No tokens, real provider data or secrets in code, fixtures or logs
- [ ] Only documented elTOQUE behavior is relied on (see `docs/api-contract.md`)
- [ ] README/docs/examples updated and runnable; `CHANGELOG.md` updated for user-visible changes
- [ ] Commits follow Conventional Commits
