# Roadmap & Changelog

---

## Roadmap

### openframe-core

- `test_middleware_types.py` — add missing test file for ASGI type alias imports
- Remove redundant `pytest.ini` — configuration already present in `pyproject.toml`
- Pin OTel SDK dev dependency to exact version — `conftest.py` accesses `_TRACER_PROVIDER_SET_ONCE._done` directly; a patch release could rename this attribute
- Switch to Trusted Publishing on PyPI — remove `PYPI_API_TOKEN` secret, use OIDC via `pypa/gh-action-pypi-publish`

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

## 2026-06-13 — v1.0.0 Initial Release

- `openframe.core.exceptions` — `AdapterError` base class and five typed subclasses. `__str__` produces `[adapter.operation] message` rather than a raw tuple repr. `super().__init__(message)` passes only the message to `Exception.__init__`.
- `openframe.core.config` — `BaseAdapterSettings` Pydantic `BaseSettings` subclass with four common fields: `adapter_name`, `connection_timeout` (30 s), `operation_timeout` (10 s), `max_retries` (3).
- `openframe.core.ports` — `BaseRepository[T]`, `BaseProducer[T]`, `BaseConsumer[T]` as `runtime_checkable` Protocols. `BaseConsumer` uses a push-based handler model (`Callable[[T], Awaitable[None]]`).
- `openframe.core.health` — `HealthCheck` Protocol with `ping()` and `is_ready()`.
- `openframe.core.telemetry` — `setup_telemetry()`, `get_tracer()`, `get_meter()`, `record_lifecycle_event()`. Removes `_grafana_headers()` — authentication handled natively via `OTEL_EXPORTER_OTLP_HEADERS`. Replaces `MODAL_ENV` with `OPENFRAME_ENV`.
- `openframe.core.tracing` — `TracingProxy` with fixed method caching. Original template captured `method` at first access (stale snapshot). This implementation resolves fresh inside `_traced` on every invocation — safe for reconnecting adapters.
- `openframe.core.middleware` — `TelemetryMiddleware` as pure ASGI middleware (not Starlette `BaseHTTPMiddleware`). Duration metric uses unit `"s"` per OTel HTTP semantic conventions. Five metric instruments. `x-session-id` injection. Does not call `setup_telemetry()`.
- `openframe.core.middleware.types` — `ASGIScope`, `ASGIMessage`, `Receive`, `Send`, `ASGIApp` stdlib-only type aliases.
- 112 tests across 8 modules. `conftest.py` resets OTel `Once._done` guards between tests — without this, `set_tracer_provider()` silently fails from test 2 onwards.
- Published to PyPI as `openframe-core==1.0.0`.
