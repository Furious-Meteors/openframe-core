# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Watch items (architectural)

- **Three application wiring options** — `deps.py` + `lru_cache`,
  `PluginRegistry` direct, and `ApplicationBootstrap` now coexist without a
  documented hierarchy. The ambiguity is better-named than before but still
  unresolved. The next documentation pass must establish `ApplicationBootstrap`
  as the default starting point and frame the other two as explicit alternatives
  with stated conditions. Tracked in the roadmap.

- **`contracts/` five-module depth** — the `capability → context → health →
  identity → lifecycle → port` chain is clean today. The risk is a sixth or
  seventh module that doesn't stay within the single-concept-per-file rule or
  that imports from non-adjacent layers. Consolidate before expanding if either
  signal appears.

### Added

- **`openframe.core.telemetry.shutdown_telemetry()`** — flushes and shuts
  down the OTel SDK, ensuring the `BatchSpanProcessor` exports all buffered
  spans before process exit. Idempotent, never raises, resets `_INITIALISED`
  so `setup_telemetry()` can run again (useful in tests).
  `ApplicationBootstrap.stop()` calls it automatically after port shutdown.
  Templates that do not use `ApplicationBootstrap` should call it in the
  `lifespan` teardown path.

- **`openframe.core.tracing.propagation`** — W3C TraceContext inject/extract
  helpers for message-broker adapters: `inject(carrier)` writes
  `traceparent` into a header dict; `extract(carrier)` reads it back and
  returns an OTel `Context`. Centralises what was previously private inside
  the Kafka adapter so every broker adapter shares one implementation.
  Re-exported as `openframe.core.tracing.propagation`.

### Fixed

#### CI/CD

- Upgraded all GitHub Actions to Node.js 24-compatible versions, resolving
  Node.js 20 deprecation warnings across all three workflows:
  - `actions/checkout` v4 → **v5**
  - `actions/setup-python` v5 → **v6**
  - `actions/upload-artifact` v4 → **v6**
  - `actions/download-artifact` v4 → **v7**
- Removed invalid `fetch-depth` input from the `actions/upload-artifact`
  step in `python-build.yml` — this parameter belongs on `actions/checkout`,
  not on the artifact upload action.
- Renamed `skip_existing` → `skip-existing` in `pypa/gh-action-pypi-publish`
  to comply with the action's current kebab-case input convention.
- Added `attestations: false` to the PyPI publish step; token-based
  authentication disables Trusted Publishing, which also disables provenance
  attestation generation — the flag must be set explicitly to suppress the
  spurious "attestations input ignored" warning. Remove this flag (or set
  `attestations: true`) once Trusted Publishing (OIDC) is configured on PyPI.

---

## [3.0.0] — 2026-07-07

### Architecture scorecard

| Dimension | Score | Notes |
|---|---|---|
| Contract design | **9.5 / 10** | `Capability` enum closes the open-string gap; `BasePort` unification removes the dual-mechanism ambiguity. |
| Error model | **9.5 / 10** | `StrEnum` + decentralised `domain.kind` convention is the correct extensibility model for a multi-package ecosystem. |
| Testing infrastructure | **9.0 / 10** | `testing/contracts/` + `testing/fakes/` centralise what every adapter was duplicating — highest-leverage addition for the ecosystem. |
| Composition / wiring | **7.0 / 10** | `ApplicationBootstrap` names the third option, but `shutdown_telemetry()` is still missing — lifecycle is not complete. |
| Telemetry | **8.0 / 10** | Sidecar architecture, bounded-queue export, `record_error` seam — no shutdown flush hook yet.

### BREAKING CHANGE

Full clean-break redesign of the port/health/plugin contract layer. There
are no deprecated aliases and no backward-compatible shims for anything
removed below — see
[ADR-006](../docs/technical/architecture/adrs/adr-006-unified-port-lifecycle.md)
for the complete rationale.

#### Added

- **`openframe.core.contracts`** (new, apex module) — the single, unified port + lifecycle contract layer:
  - `Identity` — `runtime_checkable` Protocol: `name`, `version`, `capability`.
  - `Lifecycle` — `runtime_checkable` Protocol: `async initialize(context)`, `async shutdown()`, `async health()`.
  - `BasePort(Identity, Lifecycle, Protocol)` — `runtime_checkable`. The single base every outbound port extends.
  - `Capability(str, Enum)` — closed taxonomy: `PERSISTENCE`, `CACHE`, `QUEUE`, `SECRETS`, `FLAGS`, `STORAGE`, `TRANSPORT`, `INFERENCE`, `EMBEDDING`, `SCHEDULE`, `SEARCH`.
  - `PluginStatus`, `PluginHealth`, `PluginContext` — moved here from the deleted `plugins/contracts.py`; the one canonical home.
  - `PrincipalContext`, `TenantContext` — new frozen dataclasses threaded through `PluginContext` and (on the inbound side) `RequestContext`.
- **`openframe.core.inbound`** (new module) — the driving side of the hexagon:
  - `UseCase[TInput, TOutput]`, `CommandHandler[TInput]`, `QueryHandler[TInput, TOutput]` — `runtime_checkable` Protocols.
  - `RequestContext` — frozen dataclass: correlation id + optional `PrincipalContext`/`TenantContext`.
- **`openframe.core.exceptions`** — unified error hierarchy (consolidated; see Changed/Removed below):
  - `OpenFrameError` — the single root every ecosystem error derives from. Carries `code`, `message`, `severity`, `retryable`, `correlation_id`, `context`, and `cause`. A single `except OpenFrameError` is a catch point for the whole platform.
  - `ErrorCode`, `Severity` — `StrEnum` taxonomy. Codes follow a decentralised `domain.kind` convention; downstream packages declare their own codes rather than extending the enum.
  - `AmbiguousCapabilityError` — raised by `PluginRegistry.get()` when more than one port shares a capability.
- **`openframe.core.telemetry.record_error`** — the single seam through which errors flow into telemetry: sets `error.code`/`error.severity`/`error.retryable` span attributes, records the exception, stamps `correlation_id` back onto the error, and increments the `openframe.error.count` metric exactly once per error (deduped across seams). Called at the `TracingProxy`, `TelemetryMiddleware`, and `PluginRegistry` lifecycle boundaries. `exceptions` never imports telemetry — telemetry reads the error's data.
- **`docs/technical/architecture/adrs/adr-006-unified-port-lifecycle.md`** — binding design record for this release; supersedes the port/health/plugin portions of ADR-002. Includes the unified-error-hierarchy addendum.
- **`docs/technical/architecture/capability-taxonomy.md`** — human-readable reference for the `Capability` enum.
- **`docs/technical/architecture/error-taxonomy.md`** — human-readable reference for the `OpenFrameError` hierarchy and the `domain.kind` code convention.

#### Changed

- **`openframe.core.ports`** — `BaseRepository[T]`, `BaseProducer[T]`, `BaseConsumer[T]` are rebuilt in place on `BasePort`. Every port is now lifecycle-aware by definition (`name`/`version`/`capability`/`initialize`/`shutdown`/`health` in addition to its domain methods). There is no `Managed*` twin and no lifecycle-free variant.
- **`openframe.core.plugins.registry.PluginRegistry`**
  - `register()` now accepts any `BasePort` (previously `OpenFramePlugin`) and an optional `config` mapping threaded through to `PluginContext` at initialize time.
  - `get()`/`get_all()` now take a `Capability` enum member instead of a raw `str`.
  - `get()` is now strict — raises `AmbiguousCapabilityError` when more than one port shares the requested capability, instead of silently returning the first match. Use `get_all()` for the deliberate multi-port case.
  - New `set_context(principal=..., tenant=...)` — threads a real `PrincipalContext`/`TenantContext` through every port's `PluginContext` in `initialize_all()` (previously always passed `config={}` with no identity).
- **`openframe.core.runtime.ApplicationBootstrap`** — `register()`/`get()` updated to the `BasePort`/`Capability` signatures above.
- **`openframe.core.testing.contracts`** — `RepositoryContractTests`, `ProducerContractTests`, `ConsumerContractTests` now build on the new `PortContractTests` (identity + lifecycle checks for any `BasePort`), which itself builds on `LifecycleContractTests` (initialize → health → idempotent shutdown → shutdown-before-initialize safety).
- **`openframe.core.testing.fakes`** — `InMemoryRepository`, `FakeProducer`, `FakeConsumer` now satisfy `BasePort`: each gained `name`/`version`/`capability` and `initialize`/`shutdown`/`health`.
- **`openframe.core.exceptions`** — `AdapterError` and `PluginError` are now both re-parented under the new `OpenFrameError` root. Their constructors (`AdapterError(message, adapter, operation, cause)`, `PluginError(message, plugin_name)`) and `__str__` output are unchanged, so existing raise sites and `except` clauses keep working. Each subclass now also carries a `domain.kind` `code` and a `retryable` default (`adapter.connection`/`adapter.timeout` are retryable; `adapter.not_found` is not).

#### Removed

- **`openframe.core.health`** (entire module deleted) — `HealthCheck` (`ping()`/`is_ready()`) no longer exists. Health is exclusively `Lifecycle.health() -> PluginHealth`.
- **`OpenFramePlugin`** (`openframe.core.plugins.contracts`, module deleted) — no longer exists as a separate protocol. A "plugin" is just a registered `BasePort`.
- The pre-v3 hardcoded, lifecycle-free `BaseRepository`/`BaseProducer`/`BaseConsumer` Protocols (domain methods only, no identity/lifecycle) — replaced in place, not additively.
- `InMemoryRepository.ping()`/`.is_ready()` (`ping_healthy=`/`ready_healthy=` constructor args) — replaced by `health()` (`healthy=` constructor arg).
- **`openframe.core.errors`** (entire module deleted) — the `PluginError` family (`PluginError`, `PluginInitializationError`, `PluginNotFoundError`, `DuplicatePluginError`, `AmbiguousCapabilityError`) moved into the unified `openframe.core.exceptions` package. Import from `openframe.core.exceptions` instead of `openframe.core.errors`.

### Migration notes

`openframe-adapters` packages pinned `openframe-core>=2.0,<3` continue
resolving to 2.x and are unaffected until explicitly migrated. To migrate
an adapter to v3:

1. Add `name: str`, `version: str`, `capability: Capability` attributes to every port implementation.
2. Add `async initialize(self, context: PluginContext) -> None` and `async shutdown(self) -> None`.
3. Replace `ping()`/`is_ready()` with a single `async health(self) -> PluginHealth`, encoding the liveness/readiness distinction (if you need to keep it) in `PluginStatus`/`PluginHealth.details` rather than two methods.
4. Replace any hand-written `OpenFramePlugin` wrapper class with the port object itself — it already satisfies `BasePort` once steps 1–3 are done, so no wrapper is needed.
5. Replace string capability keys (`"persistence"`) with the `Capability` enum (`Capability.PERSISTENCE`) everywhere they're used to register with or query a `PluginRegistry`.
6. Update any `from openframe.core.errors import ...` to `from openframe.core.exceptions import ...` (the `errors` package was consolidated into `exceptions`). Adapter raise sites for `AdapterError` and its subclasses need no changes — the constructors are unchanged. Optionally, catch `OpenFrameError` for a single ecosystem-wide catch point, and read `err.code`/`err.retryable`/`err.severity` instead of branching on concrete exception classes.

---

## [1.0.0] — 2026-06-13

### Added

#### `openframe.core.exceptions`
- `AdapterError` — base exception class for all OpenFrame adapter packages. Carries `message`, `adapter`, `operation`, and `cause` fields. Implements `__str__` to produce `[adapter.operation] message — caused by: <cause>` rather than a raw tuple repr.
- `AdapterConnectionError` — raised when an adapter cannot establish a connection to its backend.
- `AdapterQueryError` — raised when an operation fails after a connection is established.
- `AdapterNotFoundError` — raised when a requested entity does not exist in the backend.
- `AdapterConfigurationError` — raised when required configuration (env vars, settings) is missing or invalid.
- `AdapterTimeoutError` — raised when an operation exceeds its configured timeout.

#### `openframe.core.config`
- `BaseAdapterSettings` — Pydantic `BaseSettings` subclass that all adapter config classes inherit from. Reads fields from environment variables automatically (case-insensitive, no prefix). Ships with four common fields: `adapter_name`, `connection_timeout` (30 s), `operation_timeout` (10 s), and `max_retries` (3). Missing required fields raise `ValidationError` at instantiation time.

#### `openframe.core.ports`
- `BaseRepository[T]` — generic `runtime_checkable` Protocol for persistence adapters. Methods: `get`, `list`, `create`, `update`, `delete`.
- `BaseProducer[T]` — generic `runtime_checkable` Protocol for message producers. Methods: `publish`, `publish_batch`, `close`.
- `BaseConsumer[T]` — generic `runtime_checkable` Protocol for message consumers. Methods: `subscribe`, `ack`, `nack`, `close`. Uses a push-based handler model via `Callable[[T], Awaitable[None]]`.

#### `openframe.core.health`
- `HealthCheck` — `runtime_checkable` Protocol with two async methods: `ping()` (low-cost liveness, e.g. `SELECT 1`) and `is_ready()` (full readiness — schema migrations, pool health).

#### `openframe.core.telemetry`
- `setup_telemetry()` — idempotent OTel SDK bootstrap. Configures OTLP trace and metric exporters when `OTEL_EXPORTER_OTLP_ENDPOINT` is set; falls back to no-op providers otherwise. Applies `LoggingInstrumentor` for automatic trace-id injection into log records.
- `get_tracer(name)` — `@lru_cache` accessor for the globally-configured `Tracer`.
- `get_meter(name)` — `@lru_cache` accessor for the globally-configured `Meter`.
- `record_lifecycle_event(event_name, attributes)` — platform-agnostic lifecycle counter. Replaces the template's `record_cold_start()`; callers pass `event_name="cold_start"`. Core remains platform-agnostic.
- Reads environment variables: `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_HEADERS`, `OTEL_SERVICE_NAME`, `OTEL_SERVICE_VERSION`, `OTEL_METRIC_EXPORT_INTERVAL_MS`, `OPENFRAME_ENV`.

#### `openframe.core.tracing`
- `TracingProxy` — zero-code async telemetry sidecar. Wraps any object and intercepts every async method call with an OTel child span. Span name: `{prefix}.{method_name}`. Sync methods pass through unwrapped. Uses an explicit `_cache` dict for closure reuse without method snapshotting — safe for reconnecting adapters (Postgres pools, Redis clients) that replace their own methods after reconnect.

#### `openframe.core.middleware`
- `TelemetryMiddleware` — pure ASGI telemetry middleware, compatible with FastAPI, Starlette, Litestar, and bare ASGI. Records one OTel span and five HTTP metric instruments per request. Injects `x-session-id` response header. Sets `StatusCode.ERROR` for HTTP ≥ 400, `StatusCode.OK` otherwise. Emits a structured log line per request.
- Metric instruments: `http.server.request.count` (`1`), `http.server.request.duration` (`s`), `http.server.active_requests` (`1`), `http.server.error.count` (`1`), `http.server.response.size` (`By`). Duration uses unit `"s"` per OTel HTTP semantic conventions.
- Span attributes: `http.method`, `http.target`, `http.route`, `http.scheme`, `http.status_code`, `http.user_agent`, `net.host.name`, `http.client_ip`, `app.session_id`.
- Route template extraction: raw ASGI uses `scope["path"]`; Starlette/FastAPI users get template grouping automatically via `scope["route"].path`.

#### `openframe.core.middleware.types`
- `ASGIScope`, `ASGIMessage`, `Receive`, `Send`, `ASGIApp` — stdlib-only ASGI type aliases shared across the OpenFrame ecosystem. No framework imports required.

#### Tests
- 112 tests across 8 test modules: `test_exceptions`, `test_config`, `test_ports`, `test_health`, `test_tracing`, `test_middleware`, `test_middleware_types`, `test_config`.
- `conftest.py` resets all OTel SDK global state between tests (the `Once._done` guard on `set_tracer_provider` / `set_meter_provider`, `lru_cache` entries, and the `_INITIALISED` flag) so every test receives a clean, isolated tracer and meter.

#### Package
- `pyproject.toml` with `hatchling` build backend, `requires-python = ">=3.11"`.
- `pytest.ini` with `asyncio_mode = auto` for `pytest-asyncio`.
- Namespace package declaration in `openframe/__init__.py` via `pkgutil.extend_path`.

### Design decisions

- **Exception naming** — all exception subclasses carry the `Adapter` prefix (`AdapterConnectionError`, `AdapterTimeoutError`) to avoid shadowing the Python stdlib built-ins `ConnectionError` and `TimeoutError`.
- **No Grafana-specific auth** — `_grafana_headers()` from the production template is removed. The OTel SDK handles authentication natively via `OTEL_EXPORTER_OTLP_HEADERS`.
- **`OPENFRAME_ENV` replaces `MODAL_ENV`** — the environment tag is platform-agnostic. Modal users map `MODAL_ENV → OPENFRAME_ENV` in their `configure_env_vars()`.
- **Middleware does not call `setup_telemetry()`** — it calls `get_tracer()` and `get_meter()` directly. `setup_telemetry()` is an application startup concern (called once in a `lifespan` handler). This design makes the middleware safely composable with test fixtures that install their own providers.
- **`TracingProxy` closure safety** — the original template captured the resolved method in the closure at first access (a snapshot). This implementation resolves the method fresh on every invocation inside `_traced`, making the proxy safe for adapters that replace their own methods after reconnect.
- **Pure ASGI middleware** — uses `__call__(scope, receive, send)` rather than Starlette's `BaseHTTPMiddleware`, which has documented streaming and buffering limitations.

### Dependencies

```
opentelemetry-api>=1.24
opentelemetry-sdk>=1.24
opentelemetry-exporter-otlp-proto-http>=1.24
opentelemetry-semantic-conventions>=0.45b0
opentelemetry-instrumentation-logging>=0.45b0
pydantic>=2.0
pydantic-settings>=2.0
```

Dev dependencies: `pytest>=8.0`, `pytest-asyncio>=0.23`, `httpx>=0.27`.

---

[Unreleased]: https://github.com/openframe-org/openframe-core/compare/v3.0.0...HEAD
[3.0.0]: https://github.com/openframe-org/openframe-core/compare/v1.0.0...v3.0.0
[1.0.0]: https://github.com/openframe-org/openframe-core/releases/tag/v1.0.0
