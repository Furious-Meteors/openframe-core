# Quick Start

A working integration of `openframe-core` in 5 minutes. No Modal account required.

---

## What You'll Build

A FastAPI app that:

- Loads settings from env vars via `BaseAdapterSettings`
- Wires an in-memory repository via `TracingProxy`
- Records OTel spans locally (no external backend needed)
- Passes requests through `TelemetryMiddleware`

---

## 1. Install

```bash
pip install openframe-core fastapi uvicorn
```

---

## 2. Create the App

```python
# main.py
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException

from openframe.core.config import BaseAdapterSettings
from openframe.core.exceptions import AdapterNotFoundError
from openframe.core.health import HealthCheck
from openframe.core.middleware import TelemetryMiddleware
from openframe.core.ports import BaseRepository
from openframe.core.telemetry import record_lifecycle_event, setup_telemetry
from openframe.core.tracing import TracingProxy


# ── Settings ───────────────────────────────────────────────────────────────

class AppSettings(BaseAdapterSettings):
    app_title: str = "openframe-quickstart"


# ── In-memory repository (satisfies BaseRepository structurally) ───────────

class InMemoryRepo:
    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    async def get(self, entity_id: str) -> dict | None:
        return self._store.get(entity_id)

    async def list(self, limit: int, offset: int) -> tuple[list[dict], int]:
        items = list(self._store.values())
        return items[offset : offset + limit], len(items)

    async def create(self, entity: dict) -> dict:
        entity = {**entity, "id": str(uuid.uuid4())}
        self._store[entity["id"]] = entity
        return entity

    async def update(self, entity: dict) -> dict | None:
        if entity["id"] not in self._store:
            return None
        self._store[entity["id"]] = entity
        return entity

    async def delete(self, entity_id: str) -> bool:
        return self._store.pop(entity_id, None) is not None

    async def ping(self) -> bool:
        return True

    async def is_ready(self) -> bool:
        return True


# ── Verify structural typing ────────────────────────────────────────────────

assert isinstance(InMemoryRepo(), BaseRepository)
assert isinstance(InMemoryRepo(), HealthCheck)


# ── App wiring ──────────────────────────────────────────────────────────────

_repo = TracingProxy(InMemoryRepo(), prefix="repository.item")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_telemetry()                          # no-op if OTEL_EXPORTER_OTLP_ENDPOINT absent
    record_lifecycle_event("cold_start")
    yield


app = FastAPI(title="openframe-quickstart", lifespan=lifespan)
app.add_middleware(TelemetryMiddleware)


# ── Routes ──────────────────────────────────────────────────────────────────

@app.get("/items/{item_id}")
async def get_item(item_id: str):
    item = await _repo.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="not found")
    return item


@app.post("/items")
async def create_item(body: dict):
    return await _repo.create(body)


@app.get("/health")
async def health():
    return {"ping": await InMemoryRepo().ping()}
```

---

## 3. Run

```bash
uvicorn main:app --reload
```

---

## 4. Test

```bash
# Create an item
curl -X POST http://localhost:8000/items \
  -H "Content-Type: application/json" \
  -d '{"name": "hello"}'
# → {"name": "hello", "id": "abc-123"}

# Retrieve it
curl http://localhost:8000/items/abc-123
# → {"name": "hello", "id": "abc-123"}

# Check x-session-id header from TelemetryMiddleware
curl -v http://localhost:8000/health 2>&1 | grep x-session-id
# → x-session-id: <uuid>

# Missing item → 404
curl http://localhost:8000/items/does-not-exist
# → {"detail": "not found"}
```

---

## 5. Enable OTel Export (optional)

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="https://your-backend"
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Basic <token>"
export OTEL_SERVICE_NAME="openframe-quickstart"
uvicorn main:app
```

Every request now produces a span in your OTel backend.
