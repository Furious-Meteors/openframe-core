<p align="center">
  <img src="https://raw.githubusercontent.com/Furious-Meteors/openframe-core/production/docs/assets/images/banner.png" alt="openframe-core" width="100%" />
</p>

<p align="center">
  <a href="https://pypi.org/project/openframe-core/"><img src="https://img.shields.io/pypi/v/openframe-core?color=6DB33F&labelColor=1a1a1a&label=PyPI" alt="PyPI version"/></a>
  <a href="https://pypi.org/project/openframe-core/"><img src="https://img.shields.io/pypi/pyversions/openframe-core?color=6DB33F&labelColor=1a1a1a" alt="Python versions"/></a>
  <a href="https://github.com/Furious-Meteors/openframe-core/actions/workflows/python-build.yml"><img src="https://img.shields.io/github/actions/workflow/status/Furious-Meteors/openframe-core/python-build.yml?branch=production&color=6DB33F&labelColor=1a1a1a&label=tests" alt="Tests"/></a>
  <a href="https://github.com/Furious-Meteors/openframe-core/blob/production/LICENSE"><img src="https://img.shields.io/badge/license-MIT-6DB33F?labelColor=1a1a1a" alt="License"/></a>
  <a href="https://furious-meteors.github.io/openframe-core/"><img src="https://img.shields.io/badge/docs-live-6DB33F?labelColor=1a1a1a" alt="Docs"/></a>
</p>

<p align="center">
  <a href="https://furious-meteors.github.io/openframe-core/">Documentation</a> ·
  <a href="https://furious-meteors.github.io/openframe-core/developer-guide/quick-start/">Quick Start</a> ·
  <a href="https://pypi.org/project/openframe-core/">PyPI</a> ·
  <a href="https://github.com/Furious-Meteors/openframe-core/blob/production/.github/CHANGELOG.md">Changelog</a>
</p>

---

`openframe-core` is the foundation package of the OpenFrame Microservice Development Suite. It defines the structural contracts, telemetry primitives, and shared utilities that every other package in the ecosystem depends on.

Every package in the OpenFrame ecosystem pins `openframe-core>=3.0,<4`. The major version is the stability contract for the entire ecosystem.
---

## What's inside

| Module | Exports |
|---|---|
| `openframe.core.ports` | `BasePort` · `Identity` · `Lifecycle` · `Capability` · `PluginStatus` · `PluginHealth` · `PluginContext` · `PrincipalContext` · `TenantContext` · `BaseRepository[T]` · `BaseProducer[T]` · `BaseConsumer[T]` |
| `openframe.core.exceptions` | `OpenFrameError` (root) · `ErrorCode` · `Severity` · `AdapterError` (+5) · `PluginError` (+4, incl. `AmbiguousCapabilityError`) |
| `openframe.core.config` | `BaseAdapterSettings` — Pydantic `BaseSettings` subclass all adapters inherit |
| `openframe.core.inbound` | `UseCase[TIn, TOut]` · `CommandHandler[TIn]` · `QueryHandler[TIn, TOut]` · `RequestContext` (driving side) |
| `openframe.core.plugins` | `PluginRegistry` — explicit registration, ordered init, LIFO shutdown, capability lookup |
| `openframe.core.runtime` | `ApplicationBootstrap` — optional composition-root base class |
| `openframe.core.telemetry` | `setup_telemetry()` · `get_tracer()` · `get_meter()` · `record_lifecycle_event()` · `record_error()` |
| `openframe.core.tracing` | `TracingProxy` — zero-code async telemetry sidecar |
| `openframe.core.middleware` | `TelemetryMiddleware` — pure ASGI middleware |
| `openframe.core.middleware.types` | `ASGIScope` · `ASGIMessage` · `Receive` · `Send` · `ASGIApp` |
| `openframe.core.testing` | `InMemoryRepository` · `FakeProducer` · `FakeConsumer` · `PortContractTests` · `LifecycleContractTests` · `RepositoryContractTests` · `ProducerContractTests` · `ConsumerContractTests` |

---

## Installation

```bash
pip install openframe-core
```

```bash
# With dev dependencies (pytest, pytest-asyncio, httpx)
pip install "openframe-core[dev]"
```

---

## Quick start

### Exceptions — one catch point for the whole ecosystem

Every error derives from `OpenFrameError`, and semantics (`code`, `retryable`, `severity`) are carried as data:

```python
from openframe.core.exceptions import (
    OpenFrameError, AdapterNotFoundError, AdapterQueryError,
)

# In an adapter — wrap driver exceptions before they leave
try:
    row = await conn.fetchrow(query, entity_id)
except SomeDriverError as exc:
    raise AdapterQueryError(
        "Query failed",
        adapter="postgres",
        operation="get",
        cause=exc,
    ) from exc

# In a service — one catch point for anything the ecosystem raises
try:
    entity = await repo.get(entity_id)
except AdapterNotFoundError:
    return None
except OpenFrameError as exc:
    if exc.retryable:          # act on data, not an isinstance ladder
        await backoff_and_retry()
    logger.error("failure code=%s: %s", exc.code, exc)  # [postgres.get] ... — caused by: ...
    raise
```

Error codes follow a decentralised `domain.kind` convention (`adapter.connection`, `plugin.duplicate`); downstream packages declare their own codes and still catch cleanly under `OpenFrameError`.

### Config — env vars validated at startup, not first request

```python
from openframe.core.config import BaseAdapterSettings

class PostgresSettings(BaseAdapterSettings):
    database_url: str     # reads DATABASE_URL — required
    pool_size: int = 10   # reads POOL_SIZE — optional, default 10

# Raises pydantic_core.ValidationError immediately if DATABASE_URL is not set
settings = PostgresSettings()
```

### Ports — one lifecycle-aware base for every adapter

Every port is a `BasePort`: `Identity` (`name`/`version`/`capability`) + `Lifecycle` (`initialize`/`shutdown`/`health`) plus its own domain methods. Adapters satisfy it structurally — no inheritance required.

```python
from openframe.core.ports import Capability, PluginContext, PluginHealth, PluginStatus, BaseRepository

class PostgresItemRepository:
    # Identity
    name = "postgres-items"
    version = "1.0.0"
    capability = Capability.PERSISTENCE

    # Lifecycle
    async def initialize(self, context: PluginContext) -> None: ...
    async def shutdown(self) -> None: ...
    async def health(self) -> PluginHealth:
        return PluginHealth(status=PluginStatus.READY)

    # Domain methods
    async def get(self, entity_id: str) -> Item | None: ...
    async def list(self, limit: int, offset: int) -> tuple[list[Item], int]: ...
    async def create(self, entity: Item) -> Item: ...
    async def update(self, entity: Item) -> Item | None: ...
    async def delete(self, entity_id: str) -> bool: ...

# Structural — no BaseRepository inheritance needed
assert isinstance(PostgresItemRepository(), BaseRepository)   # True
```

### Plugins — register any port, managed lifecycle

A "plugin" is just a registered `BasePort`. The registry initializes in order, shuts down LIFO, and looks up by the typed `Capability` enum:

```python
from openframe.core.ports import Capability
from openframe.core.plugins import PluginRegistry

registry = PluginRegistry()
registry.register(PostgresItemRepository(), config={"dsn": "postgres://..."})
registry.register(RedisCache(), config={"url": "redis://..."})

await registry.initialize_all()               # forward order; rolls back on failure
repo = registry.get(Capability.PERSISTENCE)   # strict — raises if >1 match
# ... serve traffic ...
await registry.shutdown_all()                 # reverse order; never raises
```

`get()` is strict: it raises `AmbiguousCapabilityError` when more than one port shares a capability. Use `get_all(Capability.PERSISTENCE)` for the intended multi-port case (e.g. primary + replica).

### Runtime — optional composition root

```python
from openframe.core.ports import Capability
from openframe.core.runtime import ApplicationBootstrap

class MyServiceBootstrap(ApplicationBootstrap):
    def configure(self) -> None:
        self.register(PostgresItemRepository(), config={"dsn": "..."})

async with MyServiceBootstrap() as bootstrap:   # start() on enter, stop() on exit
    repo = bootstrap.get(Capability.PERSISTENCE)
    await serve(ItemService(repo))
```

### Inbound ports — the driving side of the hexagon

```python
from openframe.core.inbound import UseCase, RequestContext

class CreateItem:
    async def execute(self, command: CreateItemCommand,
                      context: RequestContext | None = None) -> Item:
        ...

assert isinstance(CreateItem(), UseCase)   # structural — no inheritance

# An inbound adapter (HTTP route, message handler, CLI) builds the context:
ctx = RequestContext(correlation_id="trace-abc")
item = await CreateItem().execute(command, ctx)
```

### Telemetry — OTel bootstrap in one call

```python
from contextlib import asynccontextmanager
from openframe.core.telemetry import setup_telemetry, record_lifecycle_event

@asynccontextmanager
async def lifespan(app):
    setup_telemetry()                      # idempotent — safe to call multiple times
    record_lifecycle_event("cold_start")   # platform-agnostic lifecycle counter
    yield
```

Configure via environment variables — no vendor lock-in:

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="https://otlp.example.com"
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Basic <base64_token>"
export OTEL_SERVICE_NAME="my-service"
export OPENFRAME_ENV="prod"
```

> **Modal users:** map `MODAL_ENV` → `OPENFRAME_ENV` in your `configure_env_vars()` helper.

### TracingProxy — spans without touching service code

```python
from openframe.core.tracing import TracingProxy

raw_repo = PostgresItemRepository(settings)
traced_repo = TracingProxy(raw_repo, prefix="repository.item")

# traced_repo.get(...)    → span "repository.item.get"
# traced_repo.create(...) → span "repository.item.create"
# The service layer never knows telemetry exists.
```

Safe for reconnecting adapters — the wrapped method is resolved fresh on every call, never snapshotted.

### Middleware — pure ASGI, framework-agnostic

```python
from openframe.core.middleware import TelemetryMiddleware

# FastAPI
app = FastAPI(lifespan=lifespan)
app.add_middleware(TelemetryMiddleware)

# Bare ASGI
app = TelemetryMiddleware(my_asgi_app)
```

> **Important:** do not call `setup_telemetry()` inside the middleware. Call it once in your `lifespan` handler. The middleware uses `get_tracer()` and `get_meter()` directly against whatever providers are currently set.

Instruments five HTTP metrics per request: `http.server.request.count`, `http.server.request.duration` (`s`), `http.server.active_requests`, `http.server.error.count`, `http.server.response.size`. Injects `x-session-id` on every response.

### Errors flow into telemetry automatically

`OpenFrameError`s are recorded into telemetry at every boundary seam — `TracingProxy` (outbound adapter calls), `TelemetryMiddleware` (inbound HTTP), and `PluginRegistry` lifecycle (startup/shutdown). Each records the exception on the active span, sets the `error.code` / `error.severity` / `error.retryable` span attributes, stamps the trace id back onto `err.correlation_id`, and increments the `openframe.error.count` metric exactly once per error. The errors layer never imports telemetry — telemetry reads the error's data — so the dependency DAG stays intact. You can also call it directly:

```python
from openframe.core.telemetry import record_error

try:
    ...
except OpenFrameError as exc:
    record_error(exc)   # span attributes + one metric increment (deduped)
    raise
```

### Testing utilities — shared fakes and contract tests

`openframe-core` ships test doubles and reusable pytest base classes that every adapter package uses, so adapters get behavioral + lifecycle conformance for free:

```python
from openframe.core.testing import InMemoryRepository, RepositoryContractTests

# In-memory BasePort implementation for fast unit tests / local dev
repo = InMemoryRepository[Item]()

# Inherit the full contract suite (CRUD + BasePort lifecycle) for your adapter
class TestPostgresRepository(RepositoryContractTests):
    @pytest.fixture
    def port(self):
        return PostgresItemRepository()
```

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | — | OTLP base URL. When absent, no-op providers are used — no errors, no export. |
| `OTEL_EXPORTER_OTLP_HEADERS` | — | Auth headers. Format: `Authorization=Basic <token>` |
| `OTEL_SERVICE_NAME` | `openframe` | Service name tag on all telemetry |
| `OTEL_SERVICE_VERSION` | `1.0.0` | Service version tag |
| `OTEL_METRIC_EXPORT_INTERVAL_MS` | `15000` | Metric export interval in milliseconds |
| `OPENFRAME_ENV` | `dev` | Deployment environment: `dev` · `feat` · `prod` |

---

## Running tests

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

301 tests. All run in under 1 second — no network calls, no external services.

```bash
# Smoke test
python -c "from openframe.core.ports import BasePort; print('openframe-core OK')"
```

---

## Design decisions

**Why one `BasePort` instead of separate port / health / plugin protocols?**
Before v3 an adapter had to satisfy three unrelated protocols (a port, `HealthCheck`, and `OpenFramePlugin`) and often hand-write a wrapper class to be registrable. `BasePort` (`Identity` + `Lifecycle`) unifies them: every port is lifecycle-aware and registry-ready with zero wrapper code. See [ADR-006](https://furious-meteors.github.io/openframe-core/technical/architecture/adrs/adr-006-unified-port-lifecycle/).

**Why a single `OpenFrameError` root?**
So a service (or gateway, or middleware) can catch anything the ecosystem raises at one point, and act on `code` / `retryable` / `severity` as data rather than importing and branching on every concrete error class. Downstream packages add their own families under the same root without widening anyone's `except`.

**Why is `Capability` a closed enum?**
Registry lookups (`registry.get(Capability.PERSISTENCE)`) are type-checked, and the duplicate-capability guard and "which capabilities exist" analysis are only possible with a closed vocabulary — no adapters inventing ad hoc capability strings.

**Why `Adapter` prefix on exceptions?**
`ConnectionError` and `TimeoutError` are Python stdlib built-ins. Using the same names would shadow them silently. `AdapterConnectionError` and `AdapterTimeoutError` are unambiguous.

**Why does `TelemetryMiddleware` not call `setup_telemetry()`?**
The OTel SDK's `set_tracer_provider()` is protected by a once-guard — subsequent calls are silently rejected. Calling `setup_telemetry()` inside the middleware overwrites the provider set at startup (including test fixture providers), causing spans to be dropped silently.

**Why is `TracingProxy` safe for reconnecting adapters?**
The closure resolves the wrapped method via `getattr(wrapped, name)` on every invocation — never from a snapshot captured at first access. When a Postgres pool or Redis client replaces its own methods after reconnect, the proxy calls the new methods automatically.

---

## Ecosystem

| Package | Install | Description |
|---|---|---|
| [`openframe-adapters`](https://github.com/Furious-Meteors/openframe-adapters) | `pip install openframe-adapters[postgres]` | DB + queue adapters — Postgres, Redis, Mongo, Kafka, NATS, and more |
| [`openframe-protocol`](https://github.com/Furious-Meteors/openframe-protocol) | `pip install openframe-protocol[sse]` | WebSocket · SSE · gRPC · MCP · webhooks |
| [`openframe-infra`](https://github.com/Furious-Meteors/openframe-infra) | `pip install openframe-infra[storage]` | Storage · auth · secrets · observability · feature flags |
| [`openframe-ai`](https://github.com/Furious-Meteors/openframe-ai) | `pip install openframe-ai[serving]` | LangChain · LlamaIndex · CrewAI · model serving · training |
| [`openframe-suite`](https://github.com/Furious-Meteors/openframe-suite) | `pip install openframe-suite[all]` | Full platform — installs everything |

All packages pin `openframe-core>=3.0,<4`.

---

## Documentation

Full documentation — architecture, module reference, runbooks, developer guide — at:

**[furious-meteors.github.io/openframe-core](https://furious-meteors.github.io/openframe-core/)**

| Section | Contents |
|---|---|
| [System Architecture](https://furious-meteors.github.io/openframe-core/technical/architecture/system-architecture/) | Unified contract layer, module dependency DAG, the hexagon's two sides |
| [ADR-006](https://furious-meteors.github.io/openframe-core/technical/architecture/adrs/adr-006-unified-port-lifecycle/) | The unified port + lifecycle contract, and the unified error hierarchy |
| [Capability Taxonomy](https://furious-meteors.github.io/openframe-core/technical/architecture/capability-taxonomy/) | The `Capability` enum reference |
| [Error Taxonomy](https://furious-meteors.github.io/openframe-core/technical/architecture/error-taxonomy/) | The `OpenFrameError` hierarchy and `domain.kind` code convention |
| [Module Reference](https://furious-meteors.github.io/openframe-core/code/modules/) | Every public class, method, parameter, return type, and raises |
| [Developer Guide](https://furious-meteors.github.io/openframe-core/developer-guide/quick-start/) | Quick start, how it works, first code change, debugging |

---

## License

MIT — see [LICENSE](LICENSE).