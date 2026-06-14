# Pipeline

Three GitHub Actions workflows. All workflows are in `.github/workflows/`.

---

## app-test.yml

Runs on every push and pull request. Installs test dependencies, runs pytest.

```yaml
trigger: push (all branches), pull_request (all branches)
python: 3.11
install: pip install -r .github/requirements/test.txt
run: pytest tests/ -v
```

Test requirements (`.github/requirements/test.txt`): `pytest>=8.0`, `pytest-asyncio>=0.23`, `httpx>=0.27`.

112 tests. All must pass. No test should take more than 1 second — all OTel tests use `InMemorySpanExporter`, no network calls.

---

## python-build.yml

Runs on push to `production` only. Builds the wheel and sdist, publishes to PyPI.

```yaml
trigger: push to production
steps:
  - hatch build          # produces dist/*.whl + dist/*.tar.gz
  - pypa/gh-action-pypi-publish  # publishes to PyPI
options:
  skip-existing: true    # re-runs don't fail on already-uploaded files
```

!!! warning
    Currently uses `PYPI_API_TOKEN` secret. Migrate to Trusted Publishing — OIDC removes the secret entirely. Setup: `https://pypi.org/manage/project/openframe-core/settings/publishing/`

---

## auto-docs.yml

Runs on push to `production` (deploy) and PRs to `dev`/`production` (build only).

```yaml
trigger: push to production → build + deploy
         PR to dev/production → build only (validate)
steps:
  - pip install -r .github/requirements/docs.txt
  - mkdocs build --strict    # --strict treats warnings as errors
  - mkdocs gh-deploy --force # production push only
```

Docs requirements (`.github/requirements/docs.txt`): `mkdocs>=1.6`, `mkdocs-material>=9.5`, `mkdocs-swagger-ui-tag>=0.6`.

Deploys to `gh-pages` branch → served at `https://furious-meteors.github.io/openframe-core/`.
