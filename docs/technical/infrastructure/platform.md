# Platform

`openframe-core` targets Modal as the reference deployment platform and PyPI as the distribution registry. Both are configurable — the package has no hard coupling to either.

---

## Distribution

| Concern | Choice | Reason |
|---|---|---|
| Public registry | [PyPI](https://pypi.org/project/openframe-core/) | Standard Python ecosystem |
| Private registry | Self-hosted devpi | All other `openframe-*` packages |
| Build toolchain | hatchling | Modern, no setup.py, workspace support |
| Python version | 3.11+ | `X | Y` union type syntax, `tomllib` stdlib |

---

## Deployment

`openframe-core` is a library — it has no runtime. It is installed as a dependency inside any Python environment. Modal is the reference deployment target for all OpenFrame templates.

| Environment | Platform | Trigger |
|---|---|---|
| `feat` | Modal | push to `feat/*` branch |
| `dev` | Modal | push to `dev` branch |
| `prod` | Modal | push to `production` branch |

The environment is set via `OPENFRAME_ENV` env var. Modal users map it from `MODAL_ENV` in `configure_env_vars()`.

---

## Future Targets

The package is platform-agnostic by design. Future `fm-infra-compute-*` packages will formalise provider-specific entry points for RunPod, Vast, GCP, AWS, and Azure. Application code in `src/` is untouched when switching providers — only the entry point file changes.
