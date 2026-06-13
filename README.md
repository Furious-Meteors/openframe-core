# openframe-core

**OpenFrame Microservice Suite — core SDK.**

`openframe-core` is the foundation package of the OpenFrame Microservice Development Suite. It defines the structural contracts, telemetry primitives, and shared utilities that every other package in the ecosystem depends on.

Every package in the OpenFrame ecosystem pins `openframe-core>=1.0,<2`. The major version is the stability contract for the entire ecosystem.

---

## What's in this package

| Module | Contents |
|--------|----------|
| `openframe.core.exceptions` | `AdapterError` hierarchy — structured exceptions all adapters raise |
| `openframe.core.config` | `BaseAdapterSettings` — Pydantic base config all adapters inherit |
| `openframe.core.ports` | `BaseRepository[T]`, `BaseProducer[T]`, `BaseConsumer[T]` Protocols |
| `openframe.core.health` | `HealthCheck` Protocol — `ping()` and `is_ready()` |
| `openframe.core.telemetry` | OTel SDK bootstrap — `setup_telemetry()`, `get_tracer()`, `get_meter()` |
| `openframe.core.tracing` | `TracingProxy` — zero-code async telemetry sidecar |
| `openframe.core.middleware` | `TelemetryMiddleware` — pure ASGI telemetry middleware |
| `openframe.core.middleware.types` | ASGI type aliases — `ASGIScope`, `ASGIMessage`, `Receive`, `Send`, `ASGIApp` |

---

## Installation

```bash
pip install openframe-core
```

For development (includes pytest, pytest-asyncio, httpx):

```bash
pip install "openframe-core[dev]"
```

---

## Quick start

### Exceptions

```python
from openframe.core.exceptions import AdapterConnectionError, AdapterNotFoundError

# In an adapter:
try:
    result = await conn.fetchrow(query)
except SomeDriverError as exc:
    raise AdapterQueryError(
        "Query failed",
        adapter="postgres",
        operation="get",
        cause=exc,
    ) from exc

# In a service (single catch point):
try:
    entity = await repo.get(entity_id)
except AdapterNotFoundError:
    return None
except AdapterError as exc:
    logger.error("Adapter failure: %s", exc)
    raise
```

### Settings

```python
from openframe.core.config import BaseAdapterSettings

class PostgresSettings(BaseAdapterSettings):
    database_url: str     # reads DATABASE_URL — required
    pool_size: int = 10   # reads POOL_SIZE — optional

# Raises ValidationError at startup if DATABASE_URL is not set:
settings = PostgresSettings()
```

### Ports

```python
from openframe.core.ports import BaseRepository

class PostgresItemRepository:
    async def get(self, entity_id: str) -> Item | None: ...
    async def list(self, limit: int, offset: int) -> tuple[list[Item], int]: ...
    async def create(self, entity: Item) -> Item: ...
    async def update(self, entity: Item) -> Item | None: ...
    async def delete(self, entity_id: str) -> bool: ...

# Structural conformance check at startup:
assert isinstance(PostgresItemRepository(), BaseRepository)
```

### Telemetry

```python
from openframe.core.telemetry import setup_telemetry, record_lifecycle_event

# In your lifespan handler — call once at startup:
@asynccontextmanager
async def lifespan(app):
    setup_telemetry()
    record_lifecycle_event("cold_start")
    yield
```

**Authentication:** Set `OTEL_EXPORTER_OTLP_HEADERS` — the OTel SDK handles it natively:

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="https://otlp.example.com"
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Basic <base64_token>"
export OTEL_SERVICE_NAME="my-service"
export OPENFRAME_ENV="prod"
```

### TracingProxy

```python
from openframe.core.tracing import TracingProxy

raw_repo = PostgresItemRepository(settings)
traced_repo = TracingProxy(raw_repo, prefix="repository.item")

# Now traced_repo.get(...)    creates span "repository.item.get"
# And traced_repo.create(...) creates span "repository.item.create"
# The service layer is unaware telemetry exists.
```

### Middleware

```python
from openframe.core.middleware import TelemetryMiddleware

# Works with FastAPI:
from fastapi import FastAPI
app = FastAPI()
app.add_middleware(TelemetryMiddleware)  # or: app = TelemetryMiddleware(app)

# Works with bare ASGI:
app = TelemetryMiddleware(my_asgi_app)
```

> **Note:** Do not call `setup_telemetry()` inside the middleware. Call it once
> in your `lifespan` handler. The middleware uses `get_tracer()` and `get_meter()`
> directly against whatever providers are currently set.

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | *(none)* | OTLP base URL. When absent, no-op providers are used. |
| `OTEL_EXPORTER_OTLP_HEADERS` | *(none)* | Auth headers, e.g. `Authorization=Basic xxx` |
| `OTEL_SERVICE_NAME` | `openframe` | Service name tag |
| `OTEL_SERVICE_VERSION` | `1.0.0` | Service version tag |
| `OTEL_METRIC_EXPORT_INTERVAL_MS` | `15000` | Metric export interval in ms |
| `OPENFRAME_ENV` | `dev` | Deployment environment: `dev` / `feat` / `prod` |

> **Modal users:** Map `MODAL_ENV` → `OPENFRAME_ENV` in your `configure_env_vars()` helper.

---

## Running tests

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

Smoke test:

```bash
python -c "from openframe.core.ports import BaseRepository; print('openframe-core OK')"
```

---

## Ecosystem packages

| Package | Description |
|---------|-------------|
| `openframe-adapters` | Database and queue adapters (Postgres, Redis, Kafka, SQS, …) |
| `openframe-protocol` | Protocol adapters (WebSocket, SSE, gRPC, MCP, webhooks) |
| `openframe-infra` | Storage, auth, secrets, observability, feature flags |
| `openframe-ai` | LangChain, LlamaIndex, CrewAI, model serving and training |
| `openframe-suite` | Top-level meta-package — installs the full suite |

All packages pin `openframe-core>=1.0,<2`.

---

## License

MIT
