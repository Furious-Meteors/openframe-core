# exceptions

`openframe/core/exceptions/errors.py` · Structured exception hierarchy for all OpenFrame adapter packages.

---

## Overview

Every adapter package raises only `AdapterError` subclasses — never raw driver exceptions. Services catch `AdapterError` at a single point regardless of which adapter is wired in. Always chain the cause at the raise site:

```python
raise AdapterQueryError(
    message="INSERT failed",
    adapter="postgres",
    operation="create",
    cause=exc,
) from exc
```

---

## Classes

### `AdapterError`

```python
class AdapterError(Exception):
    def __init__(
        self,
        message: str,
        adapter: str,
        operation: str,
        cause: Exception | None = None,
    ) -> None
```

Base exception for all OpenFrame adapter packages.

**Parameters:**

| Name | Type | Default | Description |
|---|---|---|---|
| `message` | `str` | — | Human-readable description of the failure |
| `adapter` | `str` | — | Adapter identifier, e.g. `"postgres"`, `"redis"`, `"kafka"` |
| `operation` | `str` | — | Operation that failed, e.g. `"get"`, `"create"`, `"publish"` |
| `cause` | `Exception \| None` | `None` | Underlying driver exception |

**Attributes:** `message`, `adapter`, `operation`, `cause` — all accessible as instance attributes.

**`__str__` format:**

```
[adapter.operation] message
[adapter.operation] message — caused by: <cause>
```

Example: `[postgres.get] entity not found — caused by: asyncpg.NoDataFoundError`

---

### `AdapterConnectionError`

Raised when the adapter cannot establish a connection to its backend.

Typical causes: network unreachable, wrong host/port, TLS handshake failure, authentication rejected before a connection is established.

---

### `AdapterQueryError`

Raised when an operation fails after a connection is established.

Typical causes: constraint violation, syntax error, permission denied, partial batch failure.

---

### `AdapterNotFoundError`

Raised when the requested entity does not exist in the backend.

Semantically "not found" — the adapter successfully queried the backend, but the entity is absent. Distinct from `AdapterQueryError` (query itself failed).

---

### `AdapterConfigurationError`

Raised when required configuration is missing or invalid.

Adapters should raise this at initialisation time, not at first query, so misconfigured deployments fail fast at startup.

---

### `AdapterTimeoutError`

Raised when an operation exceeds its configured timeout.

Distinct from `AdapterConnectionError` — the connection was established but the operation did not complete within the allowed window.
