# testing

`openframe/core/testing/` · Shared test doubles and reusable pytest contract test base classes.

---

## Overview

`openframe-core` ships test utilities that every adapter package uses:

- **Fakes** — in-memory `BasePort` implementations for fast unit tests and local development (no real backend needed).
- **Contract tests** — reusable pytest base classes that verify both behavioral correctness and `BasePort` lifecycle conformance.

```python
from openframe.core.testing import (
    InMemoryRepository,
    FakeProducer,
    FakeConsumer,
    PortContractTests,
    LifecycleContractTests,
    RepositoryContractTests,
    ProducerContractTests,
    ConsumerContractTests,
)
```

All three fake implementations satisfy `BasePort` — they have `name`, `version`, `capability`, `initialize`, `shutdown`, and `health`.

---

## Fakes

### `InMemoryRepository[T]`

`openframe/core/testing/fakes/repository.py`

In-memory `BaseRepository[T]` implementation backed by a plain `dict`. Satisfies `BasePort`.

```python
from openframe.core.testing import InMemoryRepository

repo = InMemoryRepository[Item]()
await repo.initialize(PluginContext())

item = await repo.create(Item(name="hello"))
found = await repo.get(item.id)
assert found == item
```

**Attributes:**

| Attribute | Value |
|---|---|
| `name` | `"in-memory-repository"` |
| `version` | `"1.0.0"` |
| `capability` | `Capability.PERSISTENCE` |

---

### `FakeProducer[T]`

`openframe/core/testing/fakes/producer.py`

In-memory `BaseProducer[T]` that stores published messages in a list. Satisfies `BasePort`.

```python
from openframe.core.testing import FakeProducer

producer = FakeProducer[Event]()
await producer.initialize(PluginContext())
await producer.publish(Event(type="created"))

assert len(producer.published) == 1
assert producer.published[0].type == "created"
```

**Additional attribute:**

| Attribute | Type | Description |
|---|---|---|
| `published` | `list[T]` | All messages published since construction |

---

### `FakeConsumer[T]`

`openframe/core/testing/fakes/consumer.py`

In-memory `BaseConsumer[T]` that drives a handler with messages injected via `inject()`. Satisfies `BasePort`.

```python
from openframe.core.testing import FakeConsumer

consumer = FakeConsumer[Event]()
await consumer.initialize(PluginContext())

received = []
await consumer.subscribe(lambda msg: received.append(msg))
await consumer.inject(Event(type="created"))

assert received[0].type == "created"
```

**Additional method:**

`inject(message)` — push a message into the consumer as if it arrived from the broker.

---

## Contract Tests

Contract test base classes verify that a `BasePort` implementation is both behaviorally correct **and** lifecycle-conformant. Every adapter package should inherit the appropriate class.

### `LifecycleContractTests`

Verifies `BasePort` lifecycle conformance: `initialize`, `shutdown`, `health`. Override the `port` fixture to provide your adapter instance.

```python
import pytest
from openframe.core.testing import LifecycleContractTests

class TestMyAdapterLifecycle(LifecycleContractTests):
    @pytest.fixture
    def port(self):
        return MyAdapter()
```

**Tests included:**

- `test_initialize_and_shutdown` — `initialize()` then `shutdown()` without error
- `test_health_returns_plugin_health` — `health()` returns a `PluginHealth` instance
- `test_health_never_raises` — `health()` does not propagate exceptions
- `test_identity_attributes` — `name`, `version`, `capability` are present and correctly typed

---

### `PortContractTests`

Extends `LifecycleContractTests`. Verifies `BasePort` structural conformance and that driver exceptions are wrapped as `OpenFrameError` subclasses (not re-raised raw).

---

### `RepositoryContractTests`

Extends `PortContractTests`. Verifies the full CRUD contract for `BaseRepository`.

```python
import pytest
from openframe.core.testing import RepositoryContractTests

class TestPostgresRepository(RepositoryContractTests):
    @pytest.fixture
    def port(self):
        return PostgresItemRepository()
```

**Tests included (in addition to `PortContractTests`):**

- `test_get_returns_none_when_missing`
- `test_create_and_get`
- `test_list_returns_count`
- `test_update_returns_none_when_missing`
- `test_delete_returns_false_when_missing`
- `test_delete_returns_true_when_present`

---

### `ProducerContractTests`

Extends `PortContractTests`. Verifies `BaseProducer` behavioral contract.

```python
class TestKafkaProducer(ProducerContractTests):
    @pytest.fixture
    def port(self):
        return KafkaProducer()
```

**Tests included:** `test_publish`, `test_publish_batch`, `test_close_is_idempotent`.

---

### `ConsumerContractTests`

Extends `PortContractTests`. Verifies `BaseConsumer` behavioral contract.

```python
class TestKafkaConsumer(ConsumerContractTests):
    @pytest.fixture
    def port(self):
        return KafkaConsumer()
```

**Tests included:** `test_subscribe_receives_message`, `test_ack`, `test_nack`, `test_close_is_idempotent`.
