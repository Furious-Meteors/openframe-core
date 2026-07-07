# telemetry

`openframe/core/telemetry/setup.py` · OTel SDK bootstrap for the OpenFrame ecosystem.

---

## Overview

Initialises the OTel SDK once — idempotent via `_INITIALISED` guard. Provides cached tracer and meter accessors. Authentication via `OTEL_EXPORTER_OTLP_HEADERS` only — no vendor-specific header construction.

!!! warning
    `TelemetryMiddleware` does NOT call `setup_telemetry()`. Call it once in the application `lifespan` handler. Calling it inside middleware silently overwrites any provider already set — including test fixture providers.

---

## Functions

### `setup_telemetry()`

```python
def setup_telemetry() -> None
```

Initialise the OTel SDK. Idempotent — safe to call multiple times; subsequent calls return immediately.

When `OTEL_EXPORTER_OTLP_ENDPOINT` is set, configures OTLP exporters for traces and metrics. When absent, installs no-op providers — no data is exported, no errors are raised.

Applies `LoggingInstrumentor` so every `logging.Logger` call automatically includes the active `trace_id` and `span_id`.

**Raises:** Nothing. All errors are logged; setup degrades gracefully.

**Environment variables read:**

| Variable | Default | Description |
|---|---|---|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | — | OTLP base URL. When absent, no-op mode |
| `OTEL_EXPORTER_OTLP_HEADERS` | — | Auth headers, handled by OTel SDK |
| `OTEL_SERVICE_NAME` | `"openframe"` | Service name tag |
| `OTEL_SERVICE_VERSION` | `"1.0.0"` | Service version tag |
| `OPENFRAME_ENV` | `"dev"` | Environment tag (`dev` / `feat` / `prod`) |
| `OTEL_METRIC_EXPORT_INTERVAL_MS` | `15000` | Metric export interval ms |

---

### `get_tracer(name)`

```python
@lru_cache(maxsize=32)
def get_tracer(name: str | None = None) -> trace.Tracer
```

Return a cached `Tracer` for the given name. Uses the globally-set `TracerProvider`.

**Parameters:**

| Name | Type | Default | Description |
|---|---|---|---|
| `name` | `str \| None` | `None` | Instrumentation scope name. Defaults to `OTEL_SERVICE_NAME` or `"openframe"` |

**Returns:** `trace.Tracer`

!!! note "Test isolation"
    Call `get_tracer.cache_clear()` in test teardown to reset the cache. Without this, all tests after the first share the tracer created in the first test.

---

### `get_meter(name)`

```python
@lru_cache(maxsize=32)
def get_meter(name: str | None = None) -> metrics.Meter
```

Return a cached `Meter` for the given name. Uses the globally-set `MeterProvider`.

**Parameters:**

| Name | Type | Default | Description |
|---|---|---|---|
| `name` | `str \| None` | `None` | Instrumentation scope name. Defaults to `OTEL_SERVICE_NAME` or `"openframe"` |

**Returns:** `metrics.Meter`

---

### `record_lifecycle_event(event_name, attributes)`

```python
def record_lifecycle_event(
    event_name: str,
    attributes: dict[str, str] | None = None,
) -> None
```

Increment a named lifecycle event counter. Platform-agnostic replacement for `record_cold_start()`.

**Parameters:**

| Name | Type | Default | Description |
|---|---|---|---|
| `event_name` | `str` | — | Name of the lifecycle event, e.g. `"cold_start"`, `"worker_restart"` |
| `attributes` | `dict[str, str] \| None` | `None` | Optional key-value labels attached to this data point |

**Metric produced:** `lifecycle.<event_name>` counter, unit `1`.

**Example:**

```python
record_lifecycle_event("cold_start")
record_lifecycle_event("worker_restart", {"reason": "oom"})
```

---

### `record_error(exc, span)`

```python
def record_error(
    exc: OpenFrameError,
    span: trace.Span | None = None,
) -> None
```

Record a structured `OpenFrameError` on the active (or provided) OTel span. Called automatically at each boundary seam (`TracingProxy`, `TelemetryMiddleware`, `PluginRegistry`). Can also be called directly.

**What it does:**

1. Sets `error.code`, `error.severity`, `error.retryable` span attributes
2. Records the exception event on the active span
3. Stamps `exc.correlation_id` with the active trace id (if `correlation_id` was `None`)
4. Increments `openframe.error.count` metric with `error.code` label — **deduped**: each error object is recorded exactly once across all seams

**Parameters:**

| Name | Type | Default | Description |
|---|---|---|---|
| `exc` | `OpenFrameError` | — | The error to record |
| `span` | `trace.Span \| None` | `None` | Span to record on. Defaults to the currently active span |

**Example:**

```python
from openframe.core.telemetry import record_error
from openframe.core.exceptions import OpenFrameError

try:
    await do_something()
except OpenFrameError as exc:
    record_error(exc)   # span attributes + one metric increment (deduped)
    raise
```
