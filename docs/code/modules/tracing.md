# tracing

`openframe/core/tracing/proxy.py` · Generic async telemetry sidecar.

---

## Overview

`TracingProxy` wraps any object and intercepts every async method call, creating a child OTel span around it. Neither the adapter nor the service layer need to know telemetry exists. Apply it in `deps.py` after constructing the real adapter.

The wrapped method is resolved fresh on every invocation — safe for reconnecting adapters (Postgres pools, Redis clients) that replace their own method objects after reconnect.

---

## Classes

### `TracingProxy`

```python
class TracingProxy:
    def __init__(self, wrapped: object, prefix: str) -> None
```

**Parameters:**

| Name | Type | Description |
|---|---|---|
| `wrapped` | `object` | The object whose async methods will be instrumented |
| `prefix` | `str` | Prefix prepended to every span name, e.g. `"repository.item"` or `"queue.kafka"` |

**Span naming:** `{prefix}.{method_name}` — e.g. `"repository.item.get"`, `"queue.kafka.publish"`

**Behaviour:**

- Async methods — wrapped with an OTel child span. Closure cached in `_cache` to avoid repeated allocation.
- Sync methods — returned directly, no span, no cache.
- Method resolution — `getattr(wrapped, name)` called on every async invocation, not snapshot at first access. Safe for reconnecting drivers.

**Usage:**

```python
from openframe.core.tracing import TracingProxy
from openframe.adapters.db.postgres import PostgresRepository

repo = PostgresRepository(settings)
traced = TracingProxy(repo, prefix="repository.item")

# traced.get(entity_id) → creates span "repository.item.get"
# traced.create(entity)  → creates span "repository.item.create"
# traced.sync_method()   → passes through, no span
```

!!! note "TracingProxy and HealthCheck"
    `TracingProxy` does not implement `HealthCheck` — `ping()` and `is_ready()` on the proxy are async and will be traced, but the proxy itself does not declare the `HealthCheck` Protocol. Call `is_ready()` on the underlying adapter directly during startup checks.
