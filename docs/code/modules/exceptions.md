# exceptions

`openframe/core/exceptions/` · Unified exception hierarchy for all OpenFrame packages.

---

## Overview

All exceptions in the OpenFrame ecosystem derive from a single root, `OpenFrameError`, so a single `except OpenFrameError` is a catch point for anything the ecosystem raises. Error semantics (`code`, `retryable`, `severity`) are carried as **data** on the error object — upper layers act on them without an `isinstance` ladder.

```python
from openframe.core.exceptions import OpenFrameError, AdapterNotFoundError, AdapterQueryError

try:
    entity = await repo.get(entity_id)
except AdapterNotFoundError:
    return None
except OpenFrameError as exc:
    if exc.retryable:
        await backoff_and_retry()
    logger.error("failure code=%s: %s", exc.code, exc)
    raise
```

Always chain the cause at the raise site:

```python
raise AdapterQueryError(
    message="INSERT failed",
    adapter="postgres",
    operation="create",
    cause=exc,
) from exc
```

---

## Hierarchy

```
Exception
└── OpenFrameError
    ├── AdapterError
    │   ├── AdapterConnectionError
    │   ├── AdapterQueryError
    │   ├── AdapterNotFoundError
    │   ├── AdapterConfigurationError
    │   └── AdapterTimeoutError
    └── PluginError
        ├── PluginInitializationError
        ├── PluginNotFoundError
        ├── DuplicatePluginError
        └── AmbiguousCapabilityError
```

---

## Classes

### `OpenFrameError`

```python
class OpenFrameError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str = "openframe.error",
        severity: Severity = Severity.ERROR,
        retryable: bool = False,
        correlation_id: str | None = None,
        context: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None
```

Root exception for the entire OpenFrame ecosystem. All errors carry the same structured, serialisation-ready fields.

**Fields:**

| Name | Type | Description |
|---|---|---|
| `code` | `str` | Namespaced `domain.kind` identity (e.g. `adapter.connection`, `plugin.initialization`) |
| `message` | `str` | Human-readable description |
| `severity` | `Severity` | `WARNING` / `ERROR` / `CRITICAL` |
| `retryable` | `bool` | Whether the operation is safe to retry |
| `correlation_id` | `str \| None` | Trace id, stamped back by `record_error()` |
| `context` | `dict[str, Any]` | Structured, non-PII detail (mutable) |
| `cause` | `Exception \| None` | Underlying exception (chained with `raise ... from`) |

---

### `ErrorCode`

```python
class ErrorCode(StrEnum): ...
```

`StrEnum` enumerating the `domain.kind` codes owned by `openframe-core`. Downstream packages declare their own plain-string codes; they do **not** extend `ErrorCode`.

| Code | Class | `retryable` |
|---|---|---|
| `openframe.error` | `OpenFrameError` | `False` |
| `adapter.error` | `AdapterError` | `False` |
| `adapter.connection` | `AdapterConnectionError` | `True` |
| `adapter.query` | `AdapterQueryError` | `False` |
| `adapter.not_found` | `AdapterNotFoundError` | `False` |
| `adapter.configuration` | `AdapterConfigurationError` | `False` |
| `adapter.timeout` | `AdapterTimeoutError` | `True` |
| `plugin.error` | `PluginError` | `False` |
| `plugin.initialization` | `PluginInitializationError` | `False` |
| `plugin.not_found` | `PluginNotFoundError` | `False` |
| `plugin.duplicate` | `DuplicatePluginError` | `False` |
| `plugin.capability_ambiguous` | `AmbiguousCapabilityError` | `False` |

---

### `Severity`

```python
class Severity(StrEnum):
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
```

Carried as data on every `OpenFrameError`. Used by `record_error()` to set the `error.severity` span attribute.

---

### `AdapterError`

```python
class AdapterError(OpenFrameError):
    def __init__(
        self,
        message: str,
        adapter: str,
        operation: str,
        cause: Exception | None = None,
    ) -> None
```

Base exception for all adapter-related failures. Preserves the `[adapter.operation] message` string format.

**Parameters:**

| Name | Type | Default | Description |
|---|---|---|---|
| `message` | `str` | — | Human-readable description of the failure |
| `adapter` | `str` | — | Adapter identifier, e.g. `"postgres"`, `"redis"`, `"kafka"` |
| `operation` | `str` | — | Operation that failed, e.g. `"get"`, `"create"`, `"publish"` |
| `cause` | `Exception \| None` | `None` | Underlying driver exception |

**`__str__` format:**

```
[adapter.operation] message
[adapter.operation] message — caused by: <cause>
```

Example: `[postgres.get] entity not found — caused by: asyncpg.NoDataFoundError`

---

### `AdapterConnectionError`

Raised when the adapter cannot establish a connection to its backend.

`code = "adapter.connection"`, `retryable = True`.

Typical causes: network unreachable, wrong host/port, TLS handshake failure, authentication rejected before a connection is established.

---

### `AdapterQueryError`

Raised when an operation fails after a connection is established.

`code = "adapter.query"`.

Typical causes: constraint violation, syntax error, permission denied, partial batch failure.

---

### `AdapterNotFoundError`

Raised when the requested entity does not exist in the backend.

`code = "adapter.not_found"`.

Semantically "not found" — the adapter successfully queried the backend, but the entity is absent. Distinct from `AdapterQueryError` (query itself failed).

---

### `AdapterConfigurationError`

Raised when required configuration is missing or invalid.

`code = "adapter.configuration"`.

Adapters should raise this at initialisation time, not at first query, so misconfigured deployments fail fast at startup.

---

### `AdapterTimeoutError`

Raised when an operation exceeds its configured timeout.

`code = "adapter.timeout"`, `retryable = True`.

Distinct from `AdapterConnectionError` — the connection was established but the operation did not complete within the allowed window.

---

### `PluginError`

```python
class PluginError(OpenFrameError):
    def __init__(
        self,
        message: str,
        plugin_name: str,
        cause: Exception | None = None,
    ) -> None
```

Base exception for all plugin registry and lifecycle failures.

**Parameters:**

| Name | Type | Description |
|---|---|---|
| `message` | `str` | Human-readable description |
| `plugin_name` | `str` | Name of the port/plugin involved |
| `cause` | `Exception \| None` | Underlying exception |

---

### `PluginInitializationError`

Raised when `port.initialize()` raises during `registry.initialize_all()`.

`code = "plugin.initialization"`.

---

### `PluginNotFoundError`

Raised by `registry.get()` when no port is registered for the requested `Capability`.

`code = "plugin.not_found"`.

---

### `DuplicatePluginError`

Raised by `registry.register()` when the same port instance is registered more than once.

`code = "plugin.duplicate"`.

---

### `AmbiguousCapabilityError`

Raised by `registry.get()` when more than one port is registered for the requested `Capability`. Use `registry.get_all()` when multiple same-capability ports is the intended configuration.

`code = "plugin.capability_ambiguous"`.
