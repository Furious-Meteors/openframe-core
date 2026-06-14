# ADR-004 — Pydantic BaseSettings over Dataclasses

**Status:** Accepted — v1.0.0

---

**Chosen:** `BaseAdapterSettings` inherits from `pydantic_settings.BaseSettings`. Every adapter's settings class inherits from `BaseAdapterSettings` and declares its fields as class attributes.

**Rejected:** Python `dataclasses.dataclass` with `__post_init__` for env var reading.

**Why:** With dataclasses, every adapter must reimplement env var reading in `__post_init__`: `self.host = os.environ.get("HOST", self.host)`. This is 3-5 lines per field, replicated across 38 adapter packages. A mistyped env var name or missing `int()` cast produces a runtime error at the first request, not at startup.

Pydantic `BaseSettings` reads env vars by field name automatically, coerces types, and raises `ValidationError` at instantiation time with a clear message identifying the missing field. `PORT=abc` produces `ValidationError: port: Input should be a valid integer` at startup, not `ValueError: invalid literal for int()` at 3am during the first database call.

Pydantic is also already in the dependency tree of FastAPI (which all templates use), so it is not a new dependency — it is a formalised one.

**Consequences:** `openframe-core` depends on `pydantic>=2.0` and `pydantic-settings>=2.0`. The `pydantic-settings` package is separate from `pydantic` since v2. All adapter packages that define settings inherit this dependency transitively.
