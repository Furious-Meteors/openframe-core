# plugins

`openframe/core/plugins/` · Managed port registry with typed `Capability` lookups.

---

## Overview

`PluginRegistry` is the single managed lifecycle coordinator. Any `BasePort` can be registered. The registry initialises ports in registration order, shuts them down in LIFO order, and provides type-safe `Capability` enum lookups. A "plugin" is just a registered `BasePort` — there is no separate plugin protocol.

```python
from openframe.core.plugins import PluginRegistry
from openframe.core.contracts import Capability
```

---

## Classes

### `PluginRegistry`

```python
class PluginRegistry:
    def register(
        self,
        port: BasePort,
        config: dict[str, Any] | None = None,
    ) -> None: ...

    async def initialize_all(
        self,
        principal: PrincipalContext | None = None,
        tenant: TenantContext | None = None,
    ) -> None: ...

    async def shutdown_all(self) -> None: ...

    def get(self, capability: Capability) -> BasePort: ...

    def get_all(self, capability: Capability) -> list[BasePort]: ...
```

---

#### `register(port, config)`

Register a `BasePort` with optional config. The config dict is passed into `PluginContext.config` when `initialize_all()` is called.

**Parameters:**

| Name | Type | Default | Description |
|---|---|---|---|
| `port` | `BasePort` | — | Any `BasePort` instance (including `BaseRepository`, `BaseProducer`, `BaseConsumer`) |
| `config` | `dict[str, Any] \| None` | `None` | Port-specific configuration dict, e.g. `{"dsn": "postgres://..."}` |

**Raises:** `DuplicatePluginError` — if the same port instance is registered more than once.

---

#### `initialize_all(principal, tenant)`

Call `port.initialize(PluginContext)` on every registered port in registration order. Rolls back (shuts down already-initialised ports) if any port raises.

**Parameters:**

| Name | Type | Default | Description |
|---|---|---|---|
| `principal` | `PrincipalContext \| None` | `None` | Optional caller identity threaded into `PluginContext` |
| `tenant` | `TenantContext \| None` | `None` | Optional tenant identity threaded into `PluginContext` |

**Raises:** `PluginInitializationError` — wrapping the original exception from `port.initialize()`, after rolling back.

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
from openframe.core.contracts import Capability

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
from openframe.core.contracts import Capability

class MyApp(ApplicationBootstrap):
    def configure(self) -> None:
        self.register(PostgresItemRepository(), config={"dsn": "..."})

async with MyApp() as app:
    repo = app.get(Capability.PERSISTENCE)
```
