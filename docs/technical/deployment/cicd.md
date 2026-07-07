# CI/CD

Three GitHub Actions workflows ship with `openframe-core`. All workflow
files live in `.github/workflows/` and use Node.js 24-compatible action
versions.

---

## Workflow Overview

| Workflow | Trigger | Jobs |
|---|---|---|
| `app-test.yml` | PR to `dev` / `production`, or called by `python-build.yml` | Run pytest matrix (Python 3.11 – 3.14) |
| `python-build.yml` | push to `production` | Gate on tests → build wheel + sdist → publish to PyPI |
| `auto-docs.yml` | push to `production`, PR to `dev`/`production` | Build MkDocs (validate) → deploy to GitHub Pages |

---

## Test Workflow

```yaml
# .github/workflows/app-test.yml
strategy:
  fail-fast: false
  matrix:
    python-version: ["3.11", "3.12", "3.13", "3.14"]

steps:
  - uses: actions/checkout@v5
  - uses: actions/setup-python@v6
  - run: pip install -e .
  - run: pip install -r .github/requirements/test.txt
  - run: pytest tests/ -v --tb=short
```

All four Python legs run independently — a failure in one does not abort
the others, giving a full compatibility picture. Python 3.14 is fetched
with `allow-prereleases: true` while it remains a release candidate on
GitHub-hosted runners.

The workflow is declared with `workflow_call:` so `python-build.yml` can
invoke it as a gate before the build job starts.

---

## Publish Workflow

Three sequential, gated jobs:

1. **test** — calls `app-test.yml`; all matrix legs must pass.
2. **build** — runs `python -m build`, uploads `dist/` as a workflow
   artifact (`actions/upload-artifact@v6`, retained for 7 days).
3. **publish** — downloads the artifact (`actions/download-artifact@v7`)
   and publishes via `pypa/gh-action-pypi-publish`. Only runs on the
   `production` branch.

```yaml
# publish step options
skip-existing: true   # re-runs don't fail on already-uploaded files
attestations: false   # token auth disables Trusted Publishing; must opt out explicitly
```

!!! warning "Migrate to Trusted Publishing"
    The workflow currently authenticates with `PYPI_API_TOKEN`
    (Phase 1 / token auth). Trusted Publishing (OIDC) removes the secret
    entirely and re-enables provenance attestations. Once configured on
    PyPI, remove the `password:` input and set `attestations: true`.

    Setup URL: `https://pypi.org/manage/project/openframe-core/settings/publishing/`

    Publisher settings:
    - Workflow: `python-build.yml`
    - Environment: `pypi`

---

## Docs Workflow

```yaml
# .github/workflows/auto-docs.yml

# build-docs job (runs on every PR — validates docs compile cleanly)
- uses: actions/checkout@v5
- uses: actions/setup-python@v6
- run: mkdocs build --strict   # --strict treats warnings as errors

# deploy-docs job (production push only)
- uses: actions/checkout@v5
    fetch-depth: 0             # full history for git-revision-date plugins
- uses: actions/setup-python@v6
- run: mkdocs gh-deploy --force
  permissions: contents: write  # push to gh-pages branch
```

`--strict` treats all MkDocs warnings as errors, catching broken links and
missing pages before they reach production. The deploy job is guarded by
`if: github.event_name == 'push' && github.ref == 'refs/heads/production'`
so PRs never trigger a deploy.
