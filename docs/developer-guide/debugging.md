# Debugging Guide

Common failure patterns and how to diagnose them.

---

## OpenFrameError in Logs

Every `AdapterError` produces a structured string:

```
[postgres.get] entity not found
[kafka.publish] broker timeout — caused by: asyncio.TimeoutError
```

The format `[adapter.operation]` tells you immediately which adapter failed and which operation was running. The `cause` field carries the original driver exception. All adapter errors also carry `code`, `severity`, and `retryable`:

```python
print(exc.code)        # "adapter.timeout"
print(exc.retryable)   # True
print(exc.severity)    # "ERROR"
```

Catch at the appropriate specificity:

```python
from openframe.core.exceptions import (
    OpenFrameError,
    AdapterNotFoundError,
    AdapterTimeoutError,
    AdapterError,
)

try:
    entity = await repo.get(entity_id)
except AdapterNotFoundError:
    # Handle 404
except AdapterTimeoutError:
    # Handle timeout — maybe retry (exc.retryable == True)
except AdapterError:
    # Catch-all for unexpected adapter failures
except OpenFrameError:
    # Catch-all for plugin/registry failures too
```

---

## PluginRegistry / ApplicationBootstrap Failures

These apply identically whether you're using `PluginRegistry` directly or through `ApplicationBootstrap` (`app.get(...)`, `app.start()`) — the bootstrap delegates straight through.

**`KeyError`** — no port registered for the requested `Capability`. Verify `register(port)` was called before `get(Capability.X)`. (Note: despite the exception hierarchy also defining a `PluginNotFoundError`, `get()` actually raises a plain `KeyError` — not that class.)

**`AmbiguousCapabilityError`** — more than one port registered for the capability passed to `get()`. Use `get_all(Capability.X)` if multiple same-capability ports is intentional (`ApplicationBootstrap.get_all()` or `registry.get_all()`).

**Whatever `initialize()` raised** — `initialize_all()` does **not** wrap a failing port's exception into a `PluginInitializationError` (that class exists in the exception hierarchy but nothing in `openframe-core` currently raises it). It rolls back already-initialised ports (LIFO) and then re-raises the original exception from `initialize()` completely unchanged — catch whatever your adapter actually raises, or `OpenFrameError` for the ecosystem-wide catch point if your adapters follow that convention:

```python
from openframe.core.exceptions import OpenFrameError

try:
    await app.start()   # or: await registry.initialize_all()
except OpenFrameError as exc:
    print(exc.code, exc.retryable)   # whatever the failing port's initialize() raised
except TimeoutError:
    print("a port's init_timeout elapsed — see PluginRegistry(default_init_timeout=...)")
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

The class is missing one or more required members. In v3, `BaseRepository` extends `BasePort`, so the class must also have `name`, `version`, `capability`, `initialize`, `shutdown`, and `health` in addition to the domain methods. A common miss is omitting lifecycle members or returning `list[T]` where `tuple[list[T], int]` is required in `list()`.

Check against [ports module](../code/modules/ports.md) for the full member list.

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
