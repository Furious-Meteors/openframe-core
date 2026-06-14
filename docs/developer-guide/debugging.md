# Debugging Guide

Common failure patterns and how to diagnose them.

---

## AdapterError in Logs

Every `AdapterError` produces a structured string:

```
[postgres.get] entity not found
[kafka.publish] broker timeout — caused by: asyncio.TimeoutError
```

The format `[adapter.operation]` tells you immediately which adapter failed and which operation was running. The `cause` field carries the original driver exception.

Catch at the appropriate specificity:

```python
try:
    entity = await repo.get(entity_id)
except AdapterNotFoundError:
    # Handle 404
except AdapterTimeoutError:
    # Handle timeout — maybe retry
except AdapterError:
    # Catch-all for unexpected adapter failures
```

---

## Spans Not Appearing in OTel Backend

**Check 1: Was `setup_telemetry()` called?**

Look for `"OpenTelemetry SDK initialised"` in startup logs. If absent, `setup_telemetry()` was never called or `OTEL_EXPORTER_OTLP_ENDPOINT` was not set (no-op mode).

**Check 2: Did the middleware call `setup_telemetry()`?**

`TelemetryMiddleware` must never call `setup_telemetry()`. If it does, it overwrites the provider set at startup and all spans are dropped silently.

**Check 3: Test isolation issue?**

If spans are missing in tests, the `InMemorySpanExporter` fixture provider may have been overwritten. Verify `reset_telemetry_state` (the `autouse` fixture) is present in `conftest.py` and resets `_INITIALISED`, `get_tracer.cache_clear()`, and the OTel `Once._done` guards.

---

## ValidationError at Startup

```
pydantic_core.ValidationError: 1 validation error for PostgresSettings
database_url
  Field required [type=missing, ...]
```

A required env var is missing. Check which field failed, find the corresponding env var name (same as field name, case-insensitive), and set it.

```bash
export DATABASE_URL="postgresql://user:pass@localhost/db"
```

---

## isinstance Check Returns False

```python
isinstance(my_repo, BaseRepository)   # False — unexpected
```

The class is missing one or more required methods. Check the Protocol definition in [ports](../code/modules/ports.md) and verify all async methods have matching signatures. A common miss is returning `list[T]` where `tuple[list[T], int]` is required in `list()`.

---

## TracingProxy Not Creating Spans

Verify the `TracerProvider` is set before `TracingProxy` is used:

```python
from openframe.core.telemetry import setup_telemetry, get_tracer

setup_telemetry()          # must be called first
proxy = TracingProxy(repo, "repository.item")
await proxy.get("abc")     # span created
```

In tests: install an `InMemorySpanExporter` and call `get_tracer.cache_clear()` after setting the provider. Without the cache clear, `get_tracer()` returns the old (no-op) tracer.
