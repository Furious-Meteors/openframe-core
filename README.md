<p align="center">
  <img src="docs/assets/images/banner.png" alt="openframe-core" width="100%" />
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

Every package in the OpenFrame ecosystem pins `openframe-core>=1.0,<2`. The major version is the stability contract for the entire ecosystem.

---

## What's inside

| Module | Exports |
|---|---|
| `openframe.core.exceptions` | `AdapterError` · `AdapterConnectionError` · `AdapterQueryError` · `AdapterNotFoundError` · `AdapterConfigurationError` · `AdapterTimeoutError` |
| `openframe.core.config` | `BaseAdapterSettings` — Pydantic `BaseSettings` subclass all adapters inherit |
| `openframe.core.ports` | `BaseRepository[T]` · `BaseProducer[T]` · `BaseConsumer[T]` — `runtime_checkable` Protocols |
| `openframe.core.health` | `HealthCheck` — `ping()` and `is_ready()` Protocol |
| `openframe.core.telemetry` | `setup_telemetry()` · `get_tracer()` · `get_meter()` · `record_lifecycle_event()` |
| `openframe.core.tracing` | `TracingProxy` — zero-code async telemetry sidecar |
| `openframe.core.middleware` | `TelemetryMiddleware` — pure ASGI middleware |
| `openframe.core.middleware.types` | `ASGIScope` · `ASGIMessage` · `Receive` · `Send` · `ASGIApp` |

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

### Exceptions — single catch point across all adapters

```python
from openframe.core.exceptions import AdapterError, AdapterNotFoundError, AdapterQueryError

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

# In a service — one catch point regardless of which adapter is wired in
try:
    entity = await repo.get(entity_id)
except AdapterNotFoundError:
    return None
except AdapterError as exc:
    logger.error("Adapter failure: %s", exc)   # [postgres.get] message — caused by: ...
    raise
```

### Config — env vars validated at startup, not first request

```python
from openframe.core.config import BaseAdapterSettings

class PostgresSettings(BaseAdapterSettings):
    database_url: str     # reads DATABASE_URL — required
    pool_size: int = 10   # reads POOL_SIZE — optional, default 10

# Raises pydantic_core.ValidationError immediately if DATABASE_URL is not set
settings = PostgresSettings()
```

### Ports — structural contracts, no inheritance required

```python
from openframe.core.ports import BaseRepository

class PostgresItemRepository:
    async def get(self, entity_id: str) -> Item | None: ...
    async def list(self, limit: int, offset: int) -> tuple[list[Item], int]: ...
    async def create(self, entity: Item) -> Item: ...
    async def update(self, entity: Item) -> Item | None: ...
    async def delete(self, entity_id: str) -> bool: ...

# Structural — no BaseRepository inheritance needed
assert isinstance(PostgresItemRepository(), BaseRepository)   # True
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

112 tests across 8 modules. All run in under 1 second — no network calls, no external services.

```bash
# Smoke test
python -c "from openframe.core.ports import BaseRepository; print('openframe-core OK')"
```

---

## Design decisions

**Why `Adapter` prefix on exceptions?**
`ConnectionError` and `TimeoutError` are Python stdlib built-ins. Using the same names would shadow them silently. `AdapterConnectionError` and `AdapterTimeoutError` are unambiguous.

**Why `super().__init__(message)` only?**
`Exception.__str__` returns a tuple repr when multiple args are passed. Passing only the message keeps `str(exc)` readable: `[postgres.get] entity not found`.

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

All packages pin `openframe-core>=1.0,<2`.

---

## Documentation

Full documentation — architecture, module reference, runbooks, developer guide — at:

**[furious-meteors.github.io/openframe-core](https://furious-meteors.github.io/openframe-core/)**

| Section | Contents |
|---|---|
| [System Overview](https://furious-meteors.github.io/openframe-core/technical/overview/system-overview/) | Seven-module model, dependency order, key design properties |
| [Package Journey](https://furious-meteors.github.io/openframe-core/technical/architecture/package-journey/) | How a request flows from template wiring through adapter to response |
| [ADRs](https://furious-meteors.github.io/openframe-core/technical/architecture/adrs/adr-001-namespace/) | Five architectural decision records |
| [Module Reference](https://furious-meteors.github.io/openframe-core/code/modules/) | Every public class, method, parameter, return type, and raises |
| [Runbooks](https://furious-meteors.github.io/openframe-core/technical/operations/) | Six operational failure scenarios with recovery steps |
| [Developer Guide](https://furious-meteors.github.io/openframe-core/developer-guide/quick-start/) | Quick start, how it works, first code change, debugging |

---

## License

MIT — see [LICENSE](LICENSE).