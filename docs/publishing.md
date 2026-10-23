# Publishing to PyPI

Publication is a **manual, owner-approved** action. Nothing is uploaded by pull requests or
ordinary pushes, and no long-lived PyPI token is used: the workflow authenticates with
[PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (OIDC).

The elTOQUE API token is unrelated to PyPI: registering with elTOQUE gives API access, while the
steps below only concern distributing this SDK.

## One-time setup (repository owner)

1. **Confirm the name.** `eltoque-python` was free on PyPI on 2026-10-22 (and no `eltoque`
   distribution existed). Re-check before publishing; names are first-come, first-served.
2. **Fill in public metadata** in `pyproject.toml`: `authors`, `[project.urls]` (Homepage,
   Source, Issues, Changelog) and, if desired, badges in the README once CI and PyPI exist.
3. **Push the repository to GitHub** and protect `main` (require the `CI` checks and PRs).
4. **Create two GitHub environments** (Settings → Environments): `pypi` and `testpypi`.
   Add **required reviewers** to both so every upload needs explicit approval, and restrict
   `pypi` to tags `v*`.
5. **Register a Trusted Publisher** on each index (account → Publishing → "Add a new pending
   publisher", since the project does not exist yet):

   | Field | PyPI (`pypi.org`) | TestPyPI (`test.pypi.org`) |
   | --- | --- | --- |
   | Project name | `eltoque-python` | `eltoque-python` |
   | Owner / repository | your GitHub owner / repo | same |
   | Workflow file | `publish.yml` | `publish.yml` |
   | Environment | `pypi` | `testpypi` |

## Release checklist

1. All CI checks green on `main`.
2. `src/eltoque/_version.py` has the new version; `CHANGELOG.md` has a `## [X.Y.Z] - date`
   section (move entries out of `Unreleased`). The workflow refuses to publish if the tag,
   version and changelog disagree.
3. Re-validate the contract: <https://tasas.eltoque.com/static/swagger.json> and the
   [terms of use](https://eltoque.com/api-tasas-de-eltoque-terminos-y-condiciones-de-uso);
   record changes in [api-contract.md](api-contract.md).
4. Local verification:

   ```bash
   uv sync --locked
   uv run ruff format --check . && uv run ruff check . && uv run mypy src && uv run pytest
   rm -rf dist && uv run python -m build && uv run twine check dist/*
   unzip -l dist/*.whl            # py.typed, LICENSE and the eltoque package are present
   ```

5. **Dry run on TestPyPI:** Actions → Publish → *Run workflow* (approve the `testpypi`
   environment). Install it in a clean venv:

   ```bash
   pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ eltoque-python
   ```

6. **Release:** create an annotated tag and push it.

   ```bash
   git tag -a vX.Y.Z -m "eltoque-python X.Y.Z"
   git push origin vX.Y.Z
   ```

   Approve the `pypi` environment when prompted.
7. Verify on <https://pypi.org/project/eltoque-python/>, then `pip install eltoque-python` in a
   clean environment, and update README wording ("not published yet") and badges.

## If something goes wrong

PyPI files cannot be replaced. If a bad version is published, **yank** it and publish a new
patch version; never reuse a version number.
