# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

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

[Unreleased]: https://github.com/openframe-org/openframe-core/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/openframe-org/openframe-core/releases/tag/v1.0.0
