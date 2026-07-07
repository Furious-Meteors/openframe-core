# Pipeline

Three GitHub Actions workflows. All workflow files live in `.github/workflows/`.

All workflows use Node.js 24-compatible action versions (`actions/checkout@v5`,
`actions/setup-python@v6`, `actions/upload-artifact@v6`,
`actions/download-artifact@v7`).

---

## app-test.yml

Runs on every pull request targeting `dev` or `production`, and is also
callable as a reusable workflow by `python-build.yml`.

```yaml
trigger: pull_request (dev, production) | workflow_call
python:  3.11 · 3.12 · 3.13 · 3.14  (matrix, fail-fast: false)
install: pip install -e . && pip install -r .github/requirements/test.txt
run:     pytest tests/ -v --tb=short
```

Test requirements (`.github/requirements/test.txt`): `pytest>=8.0`,
`pytest-asyncio>=0.23`, `httpx>=0.27`.

All matrix legs run independently even when one fails (`fail-fast: false`),
giving the full compatibility picture across supported Python versions.
Python 3.14 is fetched with `allow-prereleases: true` while it remains an
RC on GitHub-hosted runners.

No test should take more than 1 second — all OTel tests use
`InMemorySpanExporter`; no network calls are made.

---

## python-build.yml

Runs on every push to `production`. The pipeline is gated: publish is
blocked until all matrix test legs pass.

```yaml
trigger: push to production

jobs:
  test  →  (calls app-test.yml — all four Python legs must pass)
  build →  python -m build   # produces dist/*.whl + dist/*.tar.gz
  publish → pypa/gh-action-pypi-publish
```

```yaml
# build job
uses: actions/checkout@v5
uses: actions/setup-python@v6  (python: 3.11)
uses: actions/upload-artifact@v6
  name: dist | path: dist/ | retention-days: 7

# publish job
uses: actions/download-artifact@v7
uses: pypa/gh-action-pypi-publish@release/v1
  password: ${{ secrets.PYPI_API_TOKEN }}
  skip-existing: true    # re-runs don't fail on already-uploaded files
  attestations: false    # token auth disables Trusted Publishing; must opt out
```

!!! warning
    Currently uses `PYPI_API_TOKEN` secret (Phase 1). Migrate to Trusted
    Publishing — OIDC removes the secret entirely and enables PyPI
    attestations. Setup: `https://pypi.org/manage/project/openframe-core/settings/publishing/`

    Once Trusted Publishing is active, remove the `password:` input and
    set `attestations: true` to re-enable provenance attestations.

---

## auto-docs.yml

Runs on push to `production` (build + deploy) and on PRs to `dev` or
`production` (build only — validates docs compile without deploying).

```yaml
trigger: push to production      → build-docs + deploy-docs
         PR to dev / production  → build-docs only

# build-docs job
uses: actions/checkout@v5
uses: actions/setup-python@v6  (python: 3.11)
run:  mkdocs build --strict    # --strict treats warnings as errors

# deploy-docs job (production push only)
uses: actions/checkout@v5  (fetch-depth: 0 — full history for git-revision-date)
uses: actions/setup-python@v6  (python: 3.11)
run:  mkdocs gh-deploy --force
permissions: contents: write   # push to gh-pages branch
```

Docs requirements (`.github/requirements/docs.txt`): `mkdocs>=1.6`,
`mkdocs-material>=9.5`, `mkdocs-swagger-ui-tag>=0.6`.

Deploys to the `gh-pages` branch → served at
`https://furious-meteors.github.io/openframe-core/`.
