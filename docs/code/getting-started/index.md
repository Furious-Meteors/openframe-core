# Getting Started

Install `openframe-core`, configure telemetry, and verify the package in under 5 minutes.

---

## Prerequisites

- Python 3.11+
- pip

---

## 1. Install

```bash
pip install openframe-core
```

---

## 2. Smoke Test

```bash
python -c "
from openframe.core.contracts import BasePort, Capability, PluginHealth, PluginStatus
from openframe.core.ports import BaseRepository, BaseProducer, BaseConsumer
from openframe.core.exceptions import OpenFrameError, AdapterError
from openframe.core.inbound import UseCase, RequestContext
from openframe.core.plugins import PluginRegistry
from openframe.core.config import BaseAdapterSettings
from openframe.core.telemetry import get_tracer, get_meter, record_error
from openframe.core.tracing import TracingProxy
from openframe.core.middleware import TelemetryMiddleware, ASGIApp
print('openframe-core OK')
"
```

---

## 3. Configure Telemetry (optional)

When `OTEL_EXPORTER_OTLP_ENDPOINT` is absent, no-op providers are used — no data exported, no errors.

| Variable | Required | Description |
|---|---|---|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | No | OTLP base URL, e.g. `https://otlp-gateway.grafana.net/otlp` |
| `OTEL_EXPORTER_OTLP_HEADERS` | No | Auth headers, e.g. `Authorization=Basic <base64_token>` |
| `OTEL_SERVICE_NAME` | No | Service name tag (default: `openframe`) |
| `OTEL_SERVICE_VERSION` | No | Service version tag (default: `1.0.0`) |
| `OPENFRAME_ENV` | No | Environment tag: `dev` / `feat` / `prod` (default: `dev`) |
| `OTEL_METRIC_EXPORT_INTERVAL_MS` | No | Metric export interval ms (default: `15000`) |

For Grafana Cloud:

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="https://otlp-gateway-prod-us-central-0.grafana.net/otlp"
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Basic $(echo -n '<user>:<token>' | base64)"
export OTEL_SERVICE_NAME="my-service"
export OPENFRAME_ENV="dev"
```

---

## 4. Minimal FastAPI Integration

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from openframe.core.contracts import Capability
from openframe.core.plugins import PluginRegistry
from openframe.core.telemetry import setup_telemetry, record_lifecycle_event
from openframe.core.middleware import TelemetryMiddleware

registry = PluginRegistry()

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_telemetry()                          # initialise OTel — must be first
    record_lifecycle_event("cold_start")       # record startup in metrics
    await registry.initialize_all()            # initialise all registered ports
    yield
    await registry.shutdown_all()              # LIFO shutdown

app = FastAPI(lifespan=lifespan)
app.add_middleware(TelemetryMiddleware)        # attach telemetry middleware
```

---

## 5. Build the Docs

```bash
pip install mkdocs mkdocs-material pymdown-extensions
mkdocs serve    # → http://localhost:8000
mkdocs build    # → site/
```

!!! note "Running without Modal"
    `openframe-core` has no Modal imports. All examples above run locally with plain Python and uvicorn. Modal knowledge lives in `modal_app.py` only.
