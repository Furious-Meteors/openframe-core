# inbound

`openframe/core/inbound/` · The driving side of the hexagon.

---

## Overview

`inbound` gives first-class representation to the driving side of the hexagonal architecture. `UseCase`, `CommandHandler`, and `QueryHandler` are the structural contracts that inbound adapters (HTTP routes via `TelemetryMiddleware`, message handlers, CLI commands) invoke. `RequestContext` carries the per-request correlation id and optional identity.

```python
from openframe.core.inbound import (
    UseCase,
    CommandHandler,
    QueryHandler,
    RequestContext,
)
```

---

## Protocols

### `UseCase[TIn, TOut]`

```python
@runtime_checkable
class UseCase(Protocol[TIn, TOut]):
    async def execute(
        self,
        input: TIn,
        context: RequestContext | None = None,
    ) -> TOut: ...
```

General driving-side contract. Inbound adapters build a `RequestContext` and call `execute()`.

```python
class GetItem:
    async def execute(
        self,
        query: GetItemQuery,
        context: RequestContext | None = None,
    ) -> Item | None:
        return await self._repo.get(query.item_id)

assert isinstance(GetItem(), UseCase)   # structural — no inheritance needed
```

---

### `CommandHandler[TIn]`

```python
@runtime_checkable
class CommandHandler(Protocol[TIn]):
    async def execute(
        self,
        command: TIn,
        context: RequestContext | None = None,
    ) -> None: ...
```

CQRS-flavoured command contract. Returns `None` — commands mutate state but do not return data.

```python
class CreateItem:
    async def execute(
        self,
        command: CreateItemCommand,
        context: RequestContext | None = None,
    ) -> None:
        await self._repo.create(command.item)
```

---

### `QueryHandler[TIn, TOut]`

```python
@runtime_checkable
class QueryHandler(Protocol[TIn, TOut]):
    async def execute(
        self,
        query: TIn,
        context: RequestContext | None = None,
    ) -> TOut: ...
```

CQRS-flavoured query contract. Returns data but does not mutate state.

---

## Dataclasses

### `RequestContext`

```python
@dataclass(frozen=True)
class RequestContext:
    correlation_id: str
    principal: PrincipalContext | None = None
    tenant: TenantContext | None = None
```

Per-request context constructed by inbound adapters and passed into `execute()`. Carries a correlation id (typically the active trace id or a generated UUID) and optional identity/tenancy.

**Parameters:**

| Name | Type | Default | Description |
|---|---|---|---|
| `correlation_id` | `str` | — | Trace id, request id, or generated UUID |
| `principal` | `PrincipalContext \| None` | `None` | Caller identity |
| `tenant` | `TenantContext \| None` | `None` | Tenant identity |

**Example — constructing from an HTTP request:**

```python
from openframe.core.inbound import RequestContext

# In a FastAPI route or middleware
ctx = RequestContext(
    correlation_id=request.headers.get("x-trace-id", str(uuid.uuid4())),
)
result = await use_case.execute(command, ctx)
```

---

## Full Example

```python
from openframe.core.inbound import UseCase, RequestContext

# Use case implementation
class CreateItem:
    def __init__(self, repo: BaseRepository) -> None:
        self._repo = repo

    async def execute(
        self,
        command: CreateItemCommand,
        context: RequestContext | None = None,
    ) -> Item:
        return await self._repo.create(command.item)

# Inbound adapter (FastAPI route) builds the context
@app.post("/items")
async def create_item_route(body: CreateItemRequest):
    ctx = RequestContext(correlation_id=str(uuid.uuid4()))
    cmd = CreateItemCommand(item=body.to_item())
    return await CreateItem(get_repository()).execute(cmd, ctx)
```
