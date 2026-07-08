# ports

`openframe/core/ports/` · The unified port contract layer (ADR-006). Every other module depends on it, directly or transitively.

---

## Overview

`ports` defines the unified port + lifecycle contract family (ADR-006), plus the generic persistence and messaging port definitions built on it. Two small composable primitives — `Identity` and `Lifecycle` — compose into `BasePort`, the single base every outbound port and every registrable plugin extends. `Capability` replaces ad hoc string capability keys with a closed, typed enum taxonomy.

As of v3.1.0 this module absorbs what was previously split across `openframe.core.contracts` (the primitives below) and `openframe.core.ports` (the outbound protocols) — they are now one module with no compatibility shim at the old path. The outbound protocols additionally moved into an `outbound/` sub-module (`openframe/core/ports/outbound/`) mirroring the existing `openframe/core/inbound/` on the driving side of the hexagon; the public import path is unaffected — always `from openframe.core.ports import ...`.

```python
from openframe.core.ports import (
    BasePort,
    Capability,
    PluginContext,
    PluginHealth,
    PluginStatus,
    PrincipalContext,
    TenantContext,
    BaseRepository,
    BaseProducer,
    BaseConsumer,
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

---

## Outbound port protocols

Defined in `openframe/core/ports/outbound/` — capability-specific outbound port protocols, each `BasePort` (`Identity` + `Lifecycle`) plus its own domain methods. Adapters satisfy them structurally — no inheritance required. Any class with matching method signatures (identity, lifecycle, and domain methods) passes `isinstance` checks. Always import from the top-level `openframe.core.ports` package (`from openframe.core.ports import BaseRepository`) — the `outbound/` sub-module path is an implementation detail, not the intended import surface.

Every port is lifecycle-aware by definition — there is no lifecycle-free variant. `name`, `version`, `capability`, `initialize`, `shutdown`, and `health` are required on every adapter.

Future outbound capabilities (`BaseSecretsProvider`, `BaseObjectStore`, `BaseFeatureFlagProvider` from `openframe-infra`) will be added to `outbound/` alongside these three as the ecosystem grows.

!!! warning "Generic isinstance limitation"
    `isinstance(repo, BaseRepository)` works at runtime.
    `isinstance(repo, BaseRepository[str])` raises `TypeError`.
    Always use the unparameterised form in `isinstance` checks.

### `BaseRepository[T]`

`openframe/core/ports/outbound/repository.py`

Generic persistence port. `T` is the domain entity type.

```python
@runtime_checkable
class BaseRepository(BasePort, Protocol[T]):
    # identity + lifecycle from BasePort, plus:
    async def get(self, entity_id: str) -> T | None: ...
    async def list(self, limit: int, offset: int) -> tuple[list[T], int]: ...
    async def create(self, entity: T) -> T: ...
    async def update(self, entity: T) -> T | None: ...
    async def delete(self, entity_id: str) -> bool: ...
```

#### `get(entity_id)`

Retrieve a single entity by its identifier.

**Parameters:**

| Name | Type | Description |
|---|---|---|
| `entity_id` | `str` | Unique identifier of the entity |

**Returns:** `T | None` — the entity if found, `None` if it does not exist.

**Raises:**

| Exception | Condition |
|---|---|
| `AdapterConnectionError` | Backend unreachable |
| `AdapterQueryError` | Query failed |
| `AdapterTimeoutError` | Operation exceeded `operation_timeout` |

#### `list(limit, offset)`

Return a paginated slice and total count.

**Parameters:**

| Name | Type | Description |
|---|---|---|
| `limit` | `int` | Maximum entities to return |
| `offset` | `int` | Entities to skip from the beginning |

**Returns:** `tuple[list[T], int]` — `(entities, total_count)`. `total_count` is the count of all matching entities, not just the returned slice.

#### `create(entity)`

Persist a new entity and return it with backend-assigned fields.

**Returns:** `T` — the entity as stored, including any backend-assigned fields (e.g. generated primary key, `created_at`).

#### `update(entity)`

Persist changes to an existing entity.

**Returns:** `T | None` — the updated entity, or `None` if the entity did not exist.

#### `delete(entity_id)`

Remove an entity by identifier.

**Returns:** `bool` — `True` if deleted, `False` if the entity did not exist.

---

### `BaseProducer[T]`

`openframe/core/ports/outbound/producer.py`

Generic message producer port. `T` is the message payload type.

```python
@runtime_checkable
class BaseProducer(BasePort, Protocol[T]):
    # identity + lifecycle from BasePort, plus:
    async def publish(self, message: T) -> None: ...
    async def publish_batch(self, messages: list[T]) -> None: ...
    async def close(self) -> None: ...
```

#### `publish(message)`

Publish a single message to the queue.

**Raises:**

| Exception | Condition |
|---|---|
| `AdapterConnectionError` | Broker unreachable |
| `AdapterQueryError` | Publish failed (topic not found, serialisation error) |
| `AdapterTimeoutError` | Operation exceeded `operation_timeout` |

#### `publish_batch(messages)`

Publish multiple messages. Uses the backend's native batch API when available. Atomicity guarantees depend on the backend.

#### `close()`

Flush pending messages and release producer resources. Idempotent — safe to call multiple times.

!!! note
    `close()` is a domain method for flushing pending messages. Lifecycle teardown (releasing connections, etc.) happens in `shutdown()` — the `Lifecycle` method called by `PluginRegistry.shutdown_all()`.

---

### `BaseConsumer[T]`

`openframe/core/ports/outbound/consumer.py`

Generic message consumer port. Uses a push-based handler model. `T` is the message payload type.

```python
@runtime_checkable
class BaseConsumer(BasePort, Protocol[T]):
    # identity + lifecycle from BasePort, plus:
    async def subscribe(
        self,
        handler: Callable[[T], Awaitable[None]],
    ) -> None: ...
    async def ack(self, message: T) -> None: ...
    async def nack(self, message: T) -> None: ...
    async def close(self) -> None: ...
```

#### `subscribe(handler)`

Start consuming messages and pass each to `handler`. The adapter calls `ack` on handler success, `nack` on handler exception. Typically runs until `close()` is called.

**Parameters:**

| Name | Type | Description |
|---|---|---|
| `handler` | `Callable[[T], Awaitable[None]]` | Async callable receiving one message at a time |

#### `ack(message)`

Acknowledge successful processing. Signals the broker not to redeliver.

#### `nack(message)`

Negatively acknowledge. Signals the broker the message was not processed — may requeue, dead-letter, or discard depending on broker config.

#### `close()`

Stop consuming and release resources. Idempotent.

---

## Example: full BasePort implementation

```python
from openframe.core.ports import Capability, PluginContext, PluginHealth, PluginStatus
from openframe.core.ports import BaseRepository

class PostgresItemRepository:
    # Identity
    name = "postgres-items"
    version = "1.0.0"
    capability = Capability.PERSISTENCE

    # Lifecycle
    async def initialize(self, context: PluginContext) -> None:
        self._pool = await asyncpg.create_pool(context.config["dsn"])

    async def shutdown(self) -> None:
        await self._pool.close()

    async def health(self) -> PluginHealth:
        try:
            await self._pool.fetchval("SELECT 1")
            return PluginHealth(status=PluginStatus.READY)
        except Exception as exc:
            return PluginHealth(status=PluginStatus.UNAVAILABLE, message=str(exc))

    # Domain methods
    async def get(self, entity_id: str) -> Item | None: ...
    async def list(self, limit: int, offset: int) -> tuple[list[Item], int]: ...
    async def create(self, entity: Item) -> Item: ...
    async def update(self, entity: Item) -> Item | None: ...
    async def delete(self, entity_id: str) -> bool: ...

assert isinstance(PostgresItemRepository(), BaseRepository)   # True
```
