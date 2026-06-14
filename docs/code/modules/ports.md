# ports

`openframe/core/ports/` · Generic persistence and messaging port definitions.

---

## Overview

Three `runtime_checkable` Protocols. Adapters satisfy them structurally — no inheritance required. Any class with matching async method signatures passes `isinstance` checks.

!!! warning "Generic isinstance limitation"
    `isinstance(repo, BaseRepository)` works at runtime.
    `isinstance(repo, BaseRepository[str])` raises `TypeError`.
    Always use the unparameterised form in `isinstance` checks.

---

## Classes

### `BaseRepository[T]`

`openframe/core/ports/repository.py`

Generic persistence port. `T` is the domain entity type.

```python
@runtime_checkable
class BaseRepository(Protocol[T]):
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

`openframe/core/ports/producer.py`

Generic message producer port. `T` is the message payload type.

```python
@runtime_checkable
class BaseProducer(Protocol[T]):
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

---

### `BaseConsumer[T]`

`openframe/core/ports/consumer.py`

Generic message consumer port. Uses a push-based handler model. `T` is the message payload type.

```python
@runtime_checkable
class BaseConsumer(Protocol[T]):
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
