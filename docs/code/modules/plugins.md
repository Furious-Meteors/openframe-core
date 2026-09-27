# plugins

`openframe/core/plugins/` · Managed port registry with typed `Capability` lookups.

---

## Overview

`PluginRegistry` is the single managed lifecycle coordinator. Any `BasePort` can be registered. The registry initialises ports in registration order, shuts them down in LIFO order, and provides type-safe `Capability` enum lookups. A "plugin" is just a registered `BasePort` — there is no separate plugin protocol.

```python
from openframe.core.plugins import PluginRegistry
from openframe.core.ports import Capability
```

---

## Classes

### `PluginRegistry`

```python
class PluginRegistry:
    def __init__(self, *, default_init_timeout: float | None = None) -> None: ...

    def register(
        self,
        plugin: BasePort,
        *,
        config: Mapping[str, Any] | None = None,
        init_timeout: float | None = None,
    ) -> None: ...

    def set_context(
        self,
        *,
        principal: PrincipalContext | None = None,
        tenant: TenantContext | None = None,
    ) -> None: ...

    async def initialize_all(self) -> None: ...

    async def shutdown_all(self) -> None: ...

    def get(self, capability: Capability) -> BasePort: ...

    def get_all(self, capability: Capability) -> list[BasePort]: ...
```

---

#### `register(plugin, config, init_timeout)`

Register a `BasePort` with optional config and an optional per-port init timeout. The config mapping is passed into `PluginContext.config` when `initialize_all()` is called.

**Parameters:**

| Name | Type | Default | Description |
|---|---|---|---|
| `plugin` | `BasePort` | — | Any `BasePort` instance (including `BaseRepository`, `BaseProducer`, `BaseConsumer`) |
| `config` | `Mapping[str, Any] \| None` | `None` | Port-specific configuration, e.g. `{"dsn": "postgres://..."}` |
| `init_timeout` | `float \| None` | `None` | Seconds to wait for this port's `initialize()` in `initialize_all()`, overriding the registry's `default_init_timeout` for this port only. `None` falls back to that default (which is itself `None` — no timeout — unless set on the constructor) |

**Raises:** `TypeError` (object doesn't satisfy `BasePort`) · `DuplicatePluginError` — if a port with this name is already registered.

---

#### `set_context(principal, tenant)`

Set the `principal`/`tenant` threaded through every port's `PluginContext` in `initialize_all()`. Call before `initialize_all()`, typically right after all `register()` calls.

**Parameters:**

| Name | Type | Default | Description |
|---|---|---|---|
| `principal` | `PrincipalContext \| None` | `None` | Optional caller identity threaded into every port's `PluginContext` |
| `tenant` | `TenantContext \| None` | `None` | Optional tenant identity threaded into every port's `PluginContext` |

---

#### `initialize_all()`

Call `port.initialize(PluginContext)` on every registered port in registration order. Each port's config comes from its own `register()` call; `principal`/`tenant` come from `set_context()` (both default to `None` if never set). Each call is bounded by that port's `init_timeout` (or the registry's `default_init_timeout` if the port didn't specify one) — unbounded by default. Rolls back (shuts down already-initialised ports, in reverse order) if any port raises or times out, then re-raises.

**Raises:** The exception raised by the failing port's `initialize()` — or a plain `TimeoutError` if its timeout elapsed first. Neither is wrapped into a `PluginError` subclass; the registry re-raises whatever `initialize()` raised (or `TimeoutError`) unchanged, after rollback.

---

#### `shutdown_all()`

Call `port.shutdown()` on every initialised port in LIFO order. Never raises — swallows all exceptions (logs them).

---

#### `get(capability)`

Return the single registered port for the given `Capability`. **Strict**: raises when more than one port shares the capability.

**Parameters:**

| Name | Type | Description |
|---|---|---|
| `capability` | `Capability` | The capability to look up |

**Returns:** `BasePort`

**Raises:**

| Exception | Condition |
|---|---|
| `PluginNotFoundError` | No port registered for this capability |
| `AmbiguousCapabilityError` | More than one port registered for this capability |

Use `get_all()` when multiple same-capability ports is the intended configuration (e.g. primary + replica persistence pair).

---

#### `get_all(capability)`

Return all registered ports for the given `Capability`. Returns an empty list when none are registered.

**Parameters:**

| Name | Type | Description |
|---|---|---|
| `capability` | `Capability` | The capability to look up |

**Returns:** `list[BasePort]`

---

## Example

```python
from openframe.core.plugins import PluginRegistry
from openframe.core.ports import Capability

registry = PluginRegistry()

# Register during application startup
registry.register(PostgresItemRepository(), config={"dsn": "postgres://..."})
registry.register(RedisCache(), config={"url": "redis://..."})

# Initialize all ports (forward order)
await registry.initialize_all()

# Look up by capability
repo = registry.get(Capability.PERSISTENCE)   # strict — raises on >1 match
cache = registry.get(Capability.CACHE)

# Serve traffic...

# Shutdown all ports (LIFO order)
await registry.shutdown_all()
```

### Multiple same-capability ports

```python
registry.register(PrimaryPostgres(), config={...})
registry.register(ReplicaPostgres(), config={...})

# get() would raise AmbiguousCapabilityError — use get_all()
primary, replica = registry.get_all(Capability.PERSISTENCE)
```

### With ApplicationBootstrap

```python
from openframe.core.runtime import ApplicationBootstrap
from openframe.core.ports import Capability

class MyApp(ApplicationBootstrap):
    def configure(self) -> None:
        self.register(PostgresItemRepository(), config={"dsn": "..."})

async with MyApp() as app:
    repo = app.get(Capability.PERSISTENCE)
```
