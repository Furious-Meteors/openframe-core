# runtime

`openframe/core/runtime/` · The recommended composition root, at three levels of ceremony.

---

## Overview

`ApplicationBootstrap` is the single recommended composition root for application code — not one of several competing wiring patterns. It manages `PluginRegistry` registration and lifecycle for you, as an async context manager: `__aenter__` calls `start()` (which calls `configure()` then `initialize_all()`), and `__aexit__` calls `stop()` (which calls `shutdown_all()` then `shutdown_telemetry()`).

It's used at three levels of ceremony, not three separate patterns — see [Choosing a Wiring Pattern](../../developer-guide/how-it-works.md#choosing-a-wiring-pattern) for the full guide:

1. `ApplicationBootstrap.compose(*ports)` — no subclass, for one or a few ports.
2. Subclass + `configure()` — for per-port `config`/`init_timeout` or conditional registration.
3. `bootstrap.registry` — the escape hatch to the underlying `PluginRegistry` for what tiers 1-2 don't cover.

```python
from openframe.core.runtime import ApplicationBootstrap
```

---

## Classes

### `ApplicationBootstrap`

```python
class ApplicationBootstrap:
    def __init__(self, *, default_init_timeout: float | None = None) -> None: ...
    def configure(self) -> None: ...
    def register(
        self,
        plugin: BasePort,
        *,
        config: Mapping[str, Any] | None = None,
        init_timeout: float | None = None,
    ) -> None: ...
    def get(self, capability: Capability) -> BasePort: ...
    def get_all(self, capability: Capability) -> list[BasePort]: ...
    @property
    def registry(self) -> PluginRegistry: ...
    @classmethod
    def compose(cls, *ports: BasePort) -> "ApplicationBootstrap": ...
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def health(self) -> dict[str, PluginHealth]: ...

    async def __aenter__(self) -> "ApplicationBootstrap": ...
    async def __aexit__(self, *args: object) -> None: ...
```

---

#### `compose(*ports)` — classmethod

The zero-ceremony entry point. Builds an `ApplicationBootstrap` and registers each given port, in order, with no subclass. Covers the common case: settings are usually supplied at a port's own construction (e.g. `PostgresRepository(settings)`), not threaded through `PluginContext.config` — none of the four real `openframe-adapters` packages (Postgres, Mongo, Redis, Kafka) actually read `PluginContext.config` at all. Use a subclass with `configure()` instead once a port needs `config=`, `init_timeout=`, or registration order that depends on a runtime condition.

```python
async with ApplicationBootstrap.compose(PostgresRepository(settings)) as app:
    repo = app.get(Capability.PERSISTENCE)
```

---

#### `configure()`

Override this method to register ports. Called by `start()` before `initialize_all()`. The default implementation is a no-op — `compose()` never overrides it; it registers ports immediately at construction instead.

```python
class MyApp(ApplicationBootstrap):
    def configure(self) -> None:
        self.register(PostgresItemRepository(), config={"dsn": "postgres://..."})
        self.register(RedisCache(), config={"url": "redis://..."})
```

---

#### `start()`

Call `configure()` then `registry.initialize_all()`. If any port's `initialize()` raises (or its `init_timeout` elapses first), that exception propagates **unwrapped** after already-initialized ports are rolled back — `start()` does not wrap it into a `PluginInitializationError` (that class is currently unused anywhere in `openframe-core`).

---

#### `stop()`

Call `registry.shutdown_all()`, then flush and shut down the OTel SDK via `shutdown_telemetry()`. Never raises — port and telemetry errors are both logged and shutdown continues.

---

#### `register(plugin, config, init_timeout)`

Delegate to `registry.register()`. Raises `TypeError` if the object doesn't satisfy `BasePort`, or `DuplicatePluginError` if a port with this name is already registered. `init_timeout` overrides the bootstrap's own `default_init_timeout` (set on `__init__`) for this one port; `None` (the default) falls back to it.

---

#### `get(capability)`

Delegate to `registry.get()` — strict, raises `AmbiguousCapabilityError` on >1 match. Only valid after `start()` has completed.

---

#### `get_all(capability)`

Delegate to `registry.get_all()` — the escape hatch for the deliberate multi-port-per-capability case (e.g. primary + replica) that `get()`'s strictness rejects. Returns an empty list, never raises, when nothing matches.

---

#### `registry` — property

The underlying `PluginRegistry` instance. For customization neither `compose()` nor a `configure()` subclass covers (e.g. `list_plugins()`), without standing up a second, parallel registry outside `ApplicationBootstrap`.

---

#### `health()`

Delegate to `registry.health_all()` — a live health snapshot (dict of port name → `PluginHealth`) for every registered port.

---

## Usage Patterns

### Zero-ceremony — one or a few ports

```python
from openframe.core.runtime import ApplicationBootstrap
from openframe.core.ports import Capability

async with ApplicationBootstrap.compose(PostgresItemRepository()) as bootstrap:
    repo = bootstrap.get(Capability.PERSISTENCE)
    await serve(ItemService(repo))
```

### Subclass — per-port config, or conditional registration

```python
class MyServiceBootstrap(ApplicationBootstrap):
    def configure(self) -> None:
        self.register(PostgresItemRepository(), config={"dsn": "..."})

async with MyServiceBootstrap() as bootstrap:
    repo = bootstrap.get(Capability.PERSISTENCE)
    await serve(ItemService(repo))
    # shutdown_all() then shutdown_telemetry() called automatically on __aexit__
```

### As a FastAPI lifespan

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

bootstrap = ApplicationBootstrap.compose(PostgresItemRepository())

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_telemetry()
    await bootstrap.start()
    yield
    await bootstrap.stop()

app = FastAPI(lifespan=lifespan)
```

### The registry escape hatch — multi-port-per-capability

```python
async with ApplicationBootstrap.compose(PrimaryPostgres(), ReplicaPostgres()) as bootstrap:
    primary, replica = bootstrap.get_all(Capability.PERSISTENCE)
    # or, equivalently: bootstrap.registry.get_all(Capability.PERSISTENCE)
```
