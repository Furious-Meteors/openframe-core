# contracts

`openframe/core/contracts/` · The apex contract layer. Every other module depends on it, directly or transitively.

---

## Overview

`contracts` defines the unified port + lifecycle contract family (ADR-006). Two small composable primitives — `Identity` and `Lifecycle` — compose into `BasePort`, the single base every outbound port and every registrable plugin extends. `Capability` replaces ad hoc string capability keys with a closed, typed enum taxonomy.

```python
from openframe.core.contracts import (
    BasePort,
    Capability,
    PluginContext,
    PluginHealth,
    PluginStatus,
    PrincipalContext,
    TenantContext,
)
```

---

## Protocols

### `Identity`

```python
@runtime_checkable
class Identity(Protocol):
    name: str
    version: str
    capability: Capability
```

Declares what a thing *is*. All three attributes are class-level or instance attributes — no method calls.

| Attribute | Type | Description |
|---|---|---|
| `name` | `str` | Stable identifier for this port instance, e.g. `"postgres-main"` |
| `version` | `str` | Semantic version, e.g. `"1.0.0"` |
| `capability` | `Capability` | Which capability this port fulfils |

---

### `Lifecycle`

```python
@runtime_checkable
class Lifecycle(Protocol):
    async def initialize(self, context: PluginContext) -> None: ...
    async def shutdown(self) -> None: ...
    async def health(self) -> PluginHealth: ...
```

Declares how a thing is *managed*.

#### `initialize(context)`

Called by `PluginRegistry.initialize_all()` in registration order. Should connect to the backend, validate config, and acquire resources.

**Parameters:**

| Name | Type | Description |
|---|---|---|
| `context` | `PluginContext` | Carries `config`, optional `principal`, optional `tenant` |

**Raises:** `PluginInitializationError` — wrap any setup exception.

#### `shutdown()`

Called by `PluginRegistry.shutdown_all()` in LIFO order. Should flush, close connections, and release resources. Must never raise — swallow or log any errors.

#### `health()`

Return a liveness/readiness snapshot. Must never raise — return `PluginHealth(status=PluginStatus.UNAVAILABLE, message=...)` on any failure.

**Returns:** `PluginHealth`

---

### `BasePort`

```python
@runtime_checkable
class BasePort(Identity, Lifecycle, Protocol): ...
```

The single unified base every outbound port extends. A "plugin" is just a registered `BasePort` — there is no separate plugin protocol.

```python
class MyAdapter:
    name = "my-adapter"
    version = "1.0.0"
    capability = Capability.PERSISTENCE

    async def initialize(self, context: PluginContext) -> None: ...
    async def shutdown(self) -> None: ...
    async def health(self) -> PluginHealth: ...
    # ... domain methods ...

assert isinstance(MyAdapter(), BasePort)   # True — structural check
```

---

## Enums and Dataclasses

### `Capability`

```python
class Capability(str, Enum):
    PERSISTENCE = "persistence"
    CACHE       = "cache"
    QUEUE       = "queue"
    SECRETS     = "secrets"
    FLAGS       = "flags"
    STORAGE     = "storage"
    TRANSPORT   = "transport"
    INFERENCE   = "inference"
    EMBEDDING   = "embedding"
    SCHEDULE    = "schedule"
    SEARCH      = "search"
```

Closed typed taxonomy for port capabilities. Every `BasePort`'s `capability` attribute is drawn from this enum. `PluginRegistry.get()`/`get_all()` take a `Capability` member, not a raw string.

`Capability` subclasses `str`, so members compare equal to their value and serialise cleanly:

```python
assert Capability.PERSISTENCE == "persistence"
```

See [capability-taxonomy.md](../../technical/architecture/capability-taxonomy.md) for the full reference with typical adapters per member.

---

### `PluginStatus`

```python
class PluginStatus(str, Enum):
    READY       = "ready"
    DEGRADED    = "degraded"
    UNAVAILABLE = "unavailable"
```

---

### `PluginHealth`

```python
@dataclass(frozen=True)
class PluginHealth:
    status: PluginStatus
    message: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
```

Returned by `Lifecycle.health()`. Carries a status, an optional human-readable message, and optional structured detail (e.g. latency, schema checks).

```python
# Minimal
PluginHealth(status=PluginStatus.READY)

# With detail
PluginHealth(
    status=PluginStatus.READY,
    details={"ping_ms": 2.1, "schema_ok": True},
)

# Degraded
PluginHealth(
    status=PluginStatus.DEGRADED,
    message="replica lag 5s",
    details={"lag_s": 5},
)
```

---

### `PluginContext`

```python
@dataclass(frozen=True)
class PluginContext:
    config: dict[str, Any] = field(default_factory=dict)
    principal: PrincipalContext | None = None
    tenant: TenantContext | None = None
```

Passed to `Lifecycle.initialize()` by `PluginRegistry.initialize_all()`. Carries the port's config dict plus optional identity/tenancy context.

---

### `PrincipalContext`

```python
@dataclass(frozen=True)
class PrincipalContext:
    principal_id: str
    roles: frozenset[str] = field(default_factory=frozenset)
    attributes: dict[str, Any] = field(default_factory=dict)
```

Frozen dataclass carrying caller identity. Threaded through both `PluginContext` (outbound init) and `RequestContext` (inbound requests).

---

### `TenantContext`

```python
@dataclass(frozen=True)
class TenantContext:
    tenant_id: str
    attributes: dict[str, Any] = field(default_factory=dict)
```

Frozen dataclass carrying tenant identity. Threaded through both `PluginContext` and `RequestContext`.
