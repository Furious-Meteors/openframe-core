# runtime

`openframe/core/runtime/` · Optional composition root.

---

## Overview

`ApplicationBootstrap` is an optional base class that manages `PluginRegistry` registration and lifecycle for you. It is an async context manager: `__aenter__` calls `start()` (which calls `initialize_all()`), and `__aexit__` calls `stop()` (which calls `shutdown_all()`). If you prefer to manage the registry directly, you do not need `ApplicationBootstrap` at all.

```python
from openframe.core.runtime import ApplicationBootstrap
```

---

## Classes

### `ApplicationBootstrap`

```python
class ApplicationBootstrap:
    def configure(self) -> None: ...
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    def register(self, port: BasePort, config: dict | None = None) -> None: ...
    def get(self, capability: Capability) -> BasePort: ...
    def get_all(self, capability: Capability) -> list[BasePort]: ...

    async def __aenter__(self) -> "ApplicationBootstrap": ...
    async def __aexit__(self, *args: Any) -> None: ...
```

---

#### `configure()`

Override this method to register ports. Called by `start()` before `initialize_all()`. The default implementation is a no-op.

```python
class MyApp(ApplicationBootstrap):
    def configure(self) -> None:
        self.register(PostgresItemRepository(), config={"dsn": "postgres://..."})
        self.register(RedisCache(), config={"url": "redis://..."})
```

---

#### `start()`

Call `configure()` then `registry.initialize_all()`. Raises `PluginInitializationError` if any port fails to initialize.

---

#### `stop()`

Call `registry.shutdown_all()`. Never raises.

---

#### `register(port, config)`

Delegate to `registry.register()`. Raises `DuplicatePluginError` if the same port instance is registered twice.

---

#### `get(capability)` / `get_all(capability)`

Delegate to `registry.get()` / `registry.get_all()`. See [plugins module](plugins.md) for semantics.

---

## Usage Patterns

### As an async context manager

```python
from openframe.core.runtime import ApplicationBootstrap
from openframe.core.contracts import Capability

class MyServiceBootstrap(ApplicationBootstrap):
    def configure(self) -> None:
        self.register(PostgresItemRepository(), config={"dsn": "..."})

async with MyServiceBootstrap() as bootstrap:
    repo = bootstrap.get(Capability.PERSISTENCE)
    await serve(ItemService(repo))
    # shutdown_all() called automatically on __aexit__
```

### As a FastAPI lifespan

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

bootstrap = MyServiceBootstrap()

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_telemetry()
    await bootstrap.start()
    yield
    await bootstrap.stop()

app = FastAPI(lifespan=lifespan)
```

### Without ApplicationBootstrap

`ApplicationBootstrap` is optional. You can manage `PluginRegistry` directly:

```python
from openframe.core.plugins import PluginRegistry

registry = PluginRegistry()
registry.register(PostgresItemRepository(), config={"dsn": "..."})
await registry.initialize_all()
repo = registry.get(Capability.PERSISTENCE)
# ...
await registry.shutdown_all()
```
