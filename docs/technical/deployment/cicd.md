# CI/CD

Three GitHub Actions workflows ship with `openframe-core`. All run on the `production` branch.

---

## Workflow Overview

| Workflow | Trigger | Job |
|---|---|---|
| `app-test.yml` | push to any branch, PR | Run pytest suite |
| `python-build.yml` | push to `production` | Build wheel + sdist, publish to PyPI |
| `auto-docs.yml` | push to `production`, PR to `dev`/`production` | Build + deploy MkDocs to GitHub Pages |

---

## Test Workflow

```yaml
# .github/workflows/app-test.yml
- run: pip install -r .github/requirements/test.txt
- run: pytest tests/ -v
```

112 tests across 8 modules. All must pass before `python-build.yml` publishes.

---

## Publish Workflow

Builds with `hatch build`, publishes with `pypa/gh-action-pypi-publish`. Uses `skip-existing: true` to handle re-runs gracefully — PyPI rejects duplicate file uploads with a 400; the flag converts this to a warning.

!!! warning
    Switch to Trusted Publishing. The current workflow uses `PYPI_API_TOKEN`. Trusted Publishing removes the secret entirely and uses OIDC. Setup URL: `https://pypi.org/manage/project/openframe-core/settings/publishing/`

---

## Docs Workflow

```yaml
# .github/workflows/auto-docs.yml
- run: mkdocs build --strict   # on PRs — validates docs compile
- run: mkdocs gh-deploy --force  # on production push — deploys to gh-pages
```

`--strict` treats all MkDocs warnings as errors, catching broken links and missing pages before they reach production.
