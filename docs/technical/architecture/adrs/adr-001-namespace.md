# ADR-001 — Namespace: openframe/ not fm/

**Status:** Accepted — v1.0.0

---

**Chosen:** Root package directory is `openframe/`. Import paths are `openframe.core.*`. `pyproject.toml` declares `packages = ["openframe"]`.

**Rejected:** `fm/` as the root package directory. Import paths would have been `fm.core.*`.

**Why:** `fm/` was an internal shorthand for "Furious Meteors" — meaningful to the team but opaque to anyone installing the package from PyPI. `openframe` is the product name, directly matches the package name (`openframe-core`), and makes the import path self-documenting. A developer who has never seen the codebase reads `from openframe.core.ports import BaseRepository` and immediately knows which package provides it. `from fm.core.ports import BaseRepository` provides no such signal.

The inconsistency was also a technical bug: the original prompt specified `fm/` as the directory but the install verification command imported from `openframe.core`. These cannot both be true simultaneously — the directory and the import path must match.

**Consequences:** All downstream packages (`openframe-adapters`, `openframe-protocol`, etc.) must use `openframe/` as their root and declare `packages = ["openframe"]`. The `pkgutil.extend_path` namespace declaration in `openframe/__init__.py` ensures multiple packages contribute to the same `openframe.*` namespace without conflict.
