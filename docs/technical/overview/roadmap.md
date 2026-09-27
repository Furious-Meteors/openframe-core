# Roadmap & Changelog

---

## Roadmap

### openframe-core

Done since this was last updated:

- ~~Establish `ApplicationBootstrap` as the recommended wiring path~~ —
  resolved by consolidating to one class at three levels of ceremony
  (`compose()` → subclass + `configure()` → `.registry` escape hatch)
  instead of three competing patterns. See
  [Design Decisions](../architecture/design-decisions.md) and
  [How It Works § Choosing a Wiring Pattern](../../developer-guide/how-it-works.md#choosing-a-wiring-pattern).
- ~~`test_middleware_types.py`~~ — already existed (147 lines); this item
  was stale.
- ~~Remove redundant `pytest.ini`~~ — already true; no `pytest.ini` exists,
  only `[tool.pytest.ini_options]` in `pyproject.toml`. This item was
  stale.

Documentation tasks:

- (none currently open for `openframe-core` itself — see Lower-priority
  items below)

Lower-priority items:

- Pin OTel SDK dev dependency to exact version — `conftest.py`/`testing/fixtures.py`
  accesses `_TRACER_PROVIDER_SET_ONCE._done` directly; a patch release
  could rename this attribute
- Switch to Trusted Publishing on PyPI — remove `PYPI_API_TOKEN` secret, use OIDC via `pypa/gh-action-pypi-publish`
- Consider whether `PluginNotFoundError`/`PluginInitializationError` should
  actually be raised where their names imply (`PluginRegistry.get()`
  currently raises a plain `KeyError`; `initialize_all()` re-raises the
  original exception unwrapped) — both classes exist in the public
  exception hierarchy but are dead code today. Not done as part of the
  wiring-pattern consolidation since it's a behavioral change, not a
  documentation fix.

### openframe-adapters

- `openframe-adapters-db-postgres` — first adapter, reference implementation
- `openframe-adapters-db-redis` — key-value, pub/sub, semantic cache
- `openframe-adapters-db-mongo` — document store for AI Research Vault Phase 1
- `openframe-adapters-queue-kafka` — producer + consumer, unlocks event-driven template
- Remaining 11 adapters in parallel once the pattern is validated

### openframe-suite

- `openframe-suite[rest]`, `[inference]`, `[worker]` topology bundles
- Six templates: `modal-template-fastapi` (exists), `modal-template-realtime`, `modal-template-event`, `modal-template-worker`, `modal-template-inference`, `modal-template-grpc`

---

## Changelog

## v3.1.0 — contracts/ Merged into ports/, outbound/ Sub-module Introduced (breaking)

> Ecosystem packages pinned `openframe-core>=3.0,<4`; `openframe-adapters` has migrated its imports to `openframe.core.ports`.

- `openframe.core.contracts` renamed to `openframe.core.ports`. All names previously importable from `openframe.core.contracts` are now importable from `openframe.core.ports`. No compatibility shim — update all imports.
- `openframe.core.ports` now exports both the port primitives (`BasePort`, `Capability`, `Identity`, `Lifecycle`, `PluginStatus`, `PluginHealth`, `PluginContext`, `PrincipalContext`, `TenantContext`) and the outbound protocols (`BaseRepository`, `BaseProducer`, `BaseConsumer`) from a single unified module.
- `BaseRepository`, `BaseProducer`, `BaseConsumer` moved into a new `openframe/core/ports/outbound/` sub-module, mirroring `openframe/core/inbound/` on the driving side of the hexagon. The public API is unchanged — `from openframe.core.ports import BaseRepository` still works; the explicit sub-module path is now `from openframe.core.ports.outbound import BaseRepository`. Future capability-specific outbound protocols (`BaseSecretsProvider`, `BaseObjectStore`, `BaseFeatureFlagProvider` from `openframe-infra`) will be added to `ports/outbound/`.

---

## v3.0.0 — Unified Port + Lifecycle Contract (breaking)

> Migration guide: [ADR-006](../architecture/adrs/adr-006-unified-port-lifecycle.md). Ecosystem packages pinned `openframe-core>=3.0,<4`; all packages have since migrated.

**Removed:**

- `openframe.core.health` — `HealthCheck` Protocol (`ping()`/`is_ready()`) deleted. Health is now `Lifecycle.health() -> PluginHealth` in `openframe.core.ports`.
- `openframe.core.plugins.contracts` / `OpenFramePlugin` — deleted. A plugin is now just a registered `BasePort`. No separate plugin protocol exists.
- `openframe.core.errors` — the `PluginError` family moved into `openframe.core.exceptions` under the new `OpenFrameError` root. No deprecated aliases.
- Pre-v3 lifecycle-free ports — `BaseRepository`, `BaseProducer`, `BaseConsumer` no longer exist as bare domain-method-only Protocols; rebuilt on `BasePort`.

**Added:**

- `openframe.core.contracts` *(merged into `openframe.core.ports` in v3.1.0 — see below)* — apex module: `Identity`, `Lifecycle`, `BasePort` (`@runtime_checkable`), `Capability` (closed `str` enum), `PluginStatus`, `PluginHealth`, `PluginContext`, `PrincipalContext`, `TenantContext`.
- `openframe.core.inbound` — driving side of the hexagon: `UseCase[TIn, TOut]`, `CommandHandler[TIn]`, `QueryHandler[TIn, TOut]`, `RequestContext`.
- `openframe.core.exceptions.OpenFrameError` — single root for all ecosystem exceptions. `ErrorCode` and `Severity` `StrEnum`s. `AdapterError` and `PluginError` families re-parented under it.
- `openframe.core.telemetry.record_error()` — structured error→span recording seam. Called at `TracingProxy`, `TelemetryMiddleware`, and `PluginRegistry` boundary seams.
- `openframe.core.plugins.PluginRegistry` — now keys on `Capability` enum; `get()` is strict (`AmbiguousCapabilityError` on >1 match).
- `openframe.core.runtime.ApplicationBootstrap` — optional async context-manager composition root.
- `openframe.core.testing` — `InMemoryRepository`, `FakeProducer`, `FakeConsumer` (all `BasePort`-satisfying); `PortContractTests`, `LifecycleContractTests`, `RepositoryContractTests`, `ProducerContractTests`, `ConsumerContractTests`.

**Changed:**

- `BaseRepository[T]`, `BaseProducer[T]`, `BaseConsumer[T]` — now extend `BasePort`. Every port has `name`/`version`/`capability`/`initialize`/`shutdown`/`health`.
- Version bumped `2.0.0` → `3.0.0` in `pyproject.toml`.
- 284 tests. All run in under 1 second.

---

## v2.0.0 — Namespace & Settings Stabilisation (breaking)

- `openframe.core.config` — `BaseAdapterSettings` stabilised as the base for all adapter settings.
- `openframe.core.exceptions` — `AdapterError` `__str__` format locked to `[adapter.operation] message`.
- Namespace package (`pkgutil.extend_path`) stabilised. Ecosystem packages begin using the `openframe.*` namespace.

---

## 2026-06-13 — v1.0.0 Initial Release

- `openframe.core.exceptions` — `AdapterError` base class and five typed subclasses. `__str__` produces `[adapter.operation] message` rather than a raw tuple repr. `super().__init__(message)` passes only the message to `Exception.__init__`.
- `openframe.core.config` — `BaseAdapterSettings` Pydantic `BaseSettings` subclass with four common fields: `adapter_name`, `connection_timeout` (30 s), `operation_timeout` (10 s), `max_retries` (3).
- `openframe.core.ports` — `BaseRepository[T]`, `BaseProducer[T]`, `BaseConsumer[T]` as `runtime_checkable` Protocols. `BaseConsumer` uses a push-based handler model (`Callable[[T], Awaitable[None]]`).
- `openframe.core.health` — `HealthCheck` Protocol with `ping()` and `is_ready()` *(removed in v3.0.0)*.
- `openframe.core.telemetry` — `setup_telemetry()`, `get_tracer()`, `get_meter()`, `record_lifecycle_event()`. Removes `_grafana_headers()` — authentication handled natively via `OTEL_EXPORTER_OTLP_HEADERS`. Replaces `MODAL_ENV` with `OPENFRAME_ENV`.
- `openframe.core.tracing` — `TracingProxy` with fixed method caching. Original template captured `method` at first access (stale snapshot). This implementation resolves fresh inside `_traced` on every invocation — safe for reconnecting adapters.
- `openframe.core.middleware` — `TelemetryMiddleware` as pure ASGI middleware (not Starlette `BaseHTTPMiddleware`). Duration metric uses unit `"s"` per OTel HTTP semantic conventions. Five metric instruments. `x-session-id` injection. Does not call `setup_telemetry()`.
- `openframe.core.middleware.types` — `ASGIScope`, `ASGIMessage`, `Receive`, `Send`, `ASGIApp` stdlib-only type aliases.
- 112 tests across 8 modules. `conftest.py` resets OTel `Once._done` guards between tests — without this, `set_tracer_provider()` silently fails from test 2 onwards.
- Published to PyPI as `openframe-core==1.0.0`.
