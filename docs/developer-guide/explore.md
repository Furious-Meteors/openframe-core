# Explore the System

After installing `openframe-core`, explore what it provides.

---

## Browse the Namespace

```python
import openframe.core.ports
import openframe.core.exceptions
import openframe.core.inbound
import openframe.core.middleware

# All public exports
print(dir(openframe.core.ports))
# ['BaseConsumer', 'BaseProducer', 'BaseRepository', 'BasePort', 'Capability',
#  'Identity', 'Lifecycle', 'PluginContext', 'PluginHealth', 'PluginStatus',
#  'PrincipalContext', 'TenantContext', '__all__', ...]
```

---

## Verify BasePort Conformance

```python
from openframe.core.ports import (
    BasePort, Capability, PluginContext, PluginHealth, PluginStatus, BaseRepository,
)

class MyRepo:
    # Identity
    name = "my-repo"
    version = "1.0.0"
    capability = Capability.PERSISTENCE

    # Lifecycle
    async def initialize(self, context: PluginContext) -> None: pass
    async def shutdown(self) -> None: pass
    async def health(self) -> PluginHealth:
        return PluginHealth(status=PluginStatus.READY)

    # Domain methods
    async def get(self, entity_id: str): return None
    async def list(self, limit: int, offset: int): return [], 0
    async def create(self, entity): return entity
    async def update(self, entity): return entity
    async def delete(self, entity_id: str): return True

print(isinstance(MyRepo(), BasePort))         # True
print(isinstance(MyRepo(), BaseRepository))   # True

class Incomplete:
    async def get(self, entity_id: str): return None
    # missing list, create, update, delete, name, version, capability, lifecycle

print(isinstance(Incomplete(), BaseRepository))  # False
```

---

## Inspect Exception Hierarchy

```python
from openframe.core.exceptions import (
    OpenFrameError,
    AdapterError,
    AdapterConnectionError,
    AdapterQueryError,
    AdapterNotFoundError,
    AdapterConfigurationError,
    AdapterTimeoutError,
    PluginError,
    AmbiguousCapabilityError,
)

exc = AdapterNotFoundError("item missing", "postgres", "get")
print(str(exc))          # [postgres.get] item missing
print(exc.adapter)       # postgres
print(exc.operation)     # get
print(exc.code)          # adapter.not_found
print(exc.retryable)     # False
print(exc.severity)      # ERROR

print(isinstance(exc, AdapterError))     # True
print(isinstance(exc, OpenFrameError))   # True — single catch point for the ecosystem
```

---

## Explore PluginRegistry

```python
import asyncio
from openframe.core.ports import Capability
from openframe.core.plugins import PluginRegistry

registry = PluginRegistry()
registry.register(MyRepo())
asyncio.run(registry.initialize_all())

repo = registry.get(Capability.PERSISTENCE)
print(repo.name)       # my-repo
print(repo.version)    # 1.0.0

import asyncio
health = asyncio.run(repo.health())
print(health.status)   # ready

asyncio.run(registry.shutdown_all())
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
    name = "fake"
    version = "1.0.0"
    capability = Capability.PERSISTENCE
    async def initialize(self, ctx): pass
    async def shutdown(self): pass
    async def health(self): return PluginHealth(status=PluginStatus.READY)
    async def get(self, entity_id: str): return {"id": entity_id}

proxy = TracingProxy(FakeRepo(), prefix="repository.item")
asyncio.run(proxy.get("abc-123"))

spans = exporter.get_finished_spans()
print(len(spans))          # 1
print(spans[0].name)       # repository.item.get
```
