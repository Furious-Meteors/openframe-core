# Explore the System

After installing `openframe-core`, explore what it provides.

---

## Browse the Namespace

```python
import openframe.core
import openframe.core.ports
import openframe.core.exceptions
import openframe.core.middleware

# All public exports
print(dir(openframe.core.ports))
# ['BaseConsumer', 'BaseProducer', 'BaseRepository', '__all__', ...]
```

---

## Verify Protocol Conformance

```python
from openframe.core.ports import BaseRepository, BaseProducer, BaseConsumer
from openframe.core.health import HealthCheck

class MyRepo:
    async def get(self, entity_id: str): return None
    async def list(self, limit: int, offset: int): return [], 0
    async def create(self, entity): return entity
    async def update(self, entity): return entity
    async def delete(self, entity_id: str): return True
    async def ping(self) -> bool: return True
    async def is_ready(self) -> bool: return True

print(isinstance(MyRepo(), BaseRepository))   # True
print(isinstance(MyRepo(), HealthCheck))       # True

class Incomplete:
    async def get(self, entity_id: str): return None
    # missing list, create, update, delete

print(isinstance(Incomplete(), BaseRepository))  # False
```

---

## Inspect Exception Hierarchy

```python
from openframe.core.exceptions import (
    AdapterError,
    AdapterConnectionError,
    AdapterQueryError,
    AdapterNotFoundError,
    AdapterConfigurationError,
    AdapterTimeoutError,
)

exc = AdapterNotFoundError("item missing", "postgres", "get")
print(str(exc))          # [postgres.get] item missing
print(exc.adapter)       # postgres
print(exc.operation)     # get
print(exc.cause)         # None

print(isinstance(exc, AdapterError))   # True — catch all with AdapterError
```

---

## Test Telemetry Locally

```python
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry import trace
import asyncio

from openframe.core.tracing import TracingProxy
from openframe.core.telemetry import get_tracer

# Wire a test provider
exporter = InMemorySpanExporter()
provider = TracerProvider()
provider.add_span_processor(SimpleSpanProcessor(exporter))
trace.set_tracer_provider(provider)
get_tracer.cache_clear()

class FakeRepo:
    async def get(self, entity_id: str): return {"id": entity_id}

proxy = TracingProxy(FakeRepo(), prefix="repository.item")
asyncio.run(proxy.get("abc-123"))

spans = exporter.get_finished_spans()
print(len(spans))          # 1
print(spans[0].name)       # repository.item.get
```
