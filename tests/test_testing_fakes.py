"""
tests/test_testing_fakes.py
==============================
Tests for openframe.core.testing fakes and their contract conformance.

Structure
---------
- ``TestInMemoryRepositoryConformance`` — passes the full
  :class:`~openframe.core.testing.RepositoryContractTests` suite
  (including the inherited ``BasePort`` identity/lifecycle checks).
- ``TestFakeProducerConformance``        — passes the full
  :class:`~openframe.core.testing.ProducerContractTests` suite.
- ``TestFakeConsumerConformance``        — passes the full
  :class:`~openframe.core.testing.ConsumerContractTests` suite.
- Standalone functions for fake-specific behaviour not covered by the
  contract tests.
"""
from __future__ import annotations

import pytest

from openframe.core.contracts import Capability, PluginStatus
from openframe.core.exceptions import AdapterQueryError
from openframe.core.testing import (
    ConsumerContractTests,
    FakeConsumer,
    FakeProducer,
    InMemoryRepository,
    ProducerContractTests,
    RepositoryContractTests,
)


# ---------------------------------------------------------------------------
# InMemoryRepository — contract conformance
# ---------------------------------------------------------------------------


class TestInMemoryRepositoryConformance(RepositoryContractTests):
    """InMemoryRepository must pass the full RepositoryContractTests suite."""

    @pytest.fixture
    def repository(self) -> InMemoryRepository:
        """Provide a fresh InMemoryRepository for each test."""
        return InMemoryRepository()

    @pytest.fixture
    def port(self, repository: InMemoryRepository) -> InMemoryRepository:
        """Alias for the inherited PortContractTests identity/lifecycle checks."""
        return repository

    @pytest.fixture
    def make_entity(self):
        """Produce dict entities with 'id' and 'name' keys."""

        def _make(id: str, name: str = "test") -> dict:
            return {"id": id, "name": name}

        return _make


# ---------------------------------------------------------------------------
# FakeProducer — contract conformance
# ---------------------------------------------------------------------------


class TestFakeProducerConformance(ProducerContractTests):
    """FakeProducer must pass the full ProducerContractTests suite."""

    @pytest.fixture
    def producer(self) -> FakeProducer:
        """Provide a fresh FakeProducer for each test."""
        return FakeProducer()

    @pytest.fixture
    def port(self, producer: FakeProducer) -> FakeProducer:
        """Alias for the inherited PortContractTests identity/lifecycle checks."""
        return producer


# ---------------------------------------------------------------------------
# FakeConsumer — contract conformance
# ---------------------------------------------------------------------------


class TestFakeConsumerConformance(ConsumerContractTests):
    """FakeConsumer must pass the full ConsumerContractTests suite."""

    @pytest.fixture
    def consumer(self) -> FakeConsumer:
        """Provide a fresh FakeConsumer pre-seeded with two messages."""
        c: FakeConsumer[str] = FakeConsumer()
        c.feed(["msg1", "msg2"])
        return c

    @pytest.fixture
    def port(self, consumer: FakeConsumer) -> FakeConsumer:
        """Alias for the inherited PortContractTests identity/lifecycle checks."""
        return consumer


# ---------------------------------------------------------------------------
# InMemoryRepository — fake-specific tests
# ---------------------------------------------------------------------------


async def test_in_memory_repository_clear_empties_store() -> None:
    """clear() removes all entities from the store."""
    repo: InMemoryRepository[dict] = InMemoryRepository()
    await repo.create({"id": "1", "name": "alpha"})
    await repo.create({"id": "2", "name": "beta"})
    repo.clear()
    assert repo.store == {}
    _, total = await repo.list(limit=10, offset=0)
    assert total == 0


async def test_in_memory_repository_store_property_accessible() -> None:
    """store property exposes the underlying dict for test assertions."""
    repo: InMemoryRepository[dict] = InMemoryRepository()
    entity = {"id": "42", "name": "test"}
    await repo.create(entity)
    assert "42" in repo.store
    assert repo.store["42"] == entity


async def test_in_memory_repository_health_reports_failed_when_configured() -> None:
    """health() reports PluginStatus.FAILED when healthy=False."""
    repo: InMemoryRepository[dict] = InMemoryRepository(healthy=False)
    health = await repo.health()
    assert health.status is PluginStatus.FAILED


async def test_in_memory_repository_health_reports_registered_before_initialize() -> None:
    """health() reports PluginStatus.REGISTERED before initialize() is called."""
    repo: InMemoryRepository[dict] = InMemoryRepository()
    health = await repo.health()
    assert health.status is PluginStatus.REGISTERED


async def test_in_memory_repository_health_reports_ready_after_initialize() -> None:
    """health() reports PluginStatus.READY after initialize() is called."""
    from openframe.core.contracts import PluginContext

    repo: InMemoryRepository[dict] = InMemoryRepository()
    await repo.initialize(PluginContext(config={}, plugin_name=repo.name))
    health = await repo.health()
    assert health.status is PluginStatus.READY


async def test_in_memory_repository_satisfies_base_repository_protocol() -> None:
    """InMemoryRepository satisfies BaseRepository (BasePort + CRUD methods)."""
    from openframe.core.ports import BaseRepository

    repo: InMemoryRepository[dict] = InMemoryRepository()
    assert isinstance(repo, BaseRepository)


def test_in_memory_repository_default_capability_is_persistence() -> None:
    """InMemoryRepository defaults to Capability.PERSISTENCE."""
    repo: InMemoryRepository[dict] = InMemoryRepository()
    assert repo.capability == Capability.PERSISTENCE


# ---------------------------------------------------------------------------
# FakeProducer — fake-specific tests
# ---------------------------------------------------------------------------


async def test_fake_producer_records_published_messages() -> None:
    """publish() appends each message to producer.published."""
    producer: FakeProducer[str] = FakeProducer()
    await producer.publish("hello")
    await producer.publish("world")
    assert producer.published == ["hello", "world"]


async def test_fake_producer_records_batches_separately() -> None:
    """publish_batch() records the batch in batches and items in published."""
    producer: FakeProducer[str] = FakeProducer()
    await producer.publish_batch(["a", "b"])
    await producer.publish_batch(["c"])
    assert producer.published == ["a", "b", "c"]
    assert producer.batches == [["a", "b"], ["c"]]


async def test_fake_producer_raises_on_fail_mode() -> None:
    """publish() raises AdapterQueryError when fail_on_publish=True."""
    producer: FakeProducer[str] = FakeProducer(fail_on_publish=True)
    with pytest.raises(AdapterQueryError):
        await producer.publish("will-fail")


async def test_fake_producer_batch_raises_on_fail_mode() -> None:
    """publish_batch() raises AdapterQueryError when fail_on_publish=True."""
    producer: FakeProducer[str] = FakeProducer(fail_on_publish=True)
    with pytest.raises(AdapterQueryError):
        await producer.publish_batch(["will-fail"])


async def test_fake_producer_clear_resets_state() -> None:
    """clear() empties published and batches lists."""
    producer: FakeProducer[str] = FakeProducer()
    await producer.publish("x")
    await producer.publish_batch(["y"])
    producer.clear()
    assert producer.published == []
    assert producer.batches == []


def test_fake_producer_default_capability_is_queue() -> None:
    """FakeProducer defaults to Capability.QUEUE."""
    producer: FakeProducer[str] = FakeProducer()
    assert producer.capability == Capability.QUEUE


# ---------------------------------------------------------------------------
# FakeConsumer — fake-specific tests
# ---------------------------------------------------------------------------


async def test_fake_consumer_feeds_and_delivers_messages() -> None:
    """feed() + subscribe() delivers messages to the handler in order."""
    consumer: FakeConsumer[str] = FakeConsumer()
    consumer.feed(["x", "y", "z"])
    received: list[str] = []

    async def handler(msg: str) -> None:
        received.append(msg)

    await consumer.subscribe(handler)
    assert received == ["x", "y", "z"]


async def test_fake_consumer_acks_on_success() -> None:
    """subscribe() acks every message when the handler succeeds."""
    consumer: FakeConsumer[str] = FakeConsumer()
    consumer.feed(["a", "b"])

    async def handler(msg: str) -> None:
        pass

    await consumer.subscribe(handler)
    assert consumer.acked == ["a", "b"]
    assert consumer.nacked == []


async def test_fake_consumer_nacks_on_handler_failure() -> None:
    """subscribe() nacks a message when the handler raises."""
    consumer: FakeConsumer[str] = FakeConsumer()
    consumer.feed(["b"])

    async def handler(msg: str) -> None:
        raise ValueError("deliberate failure")

    await consumer.subscribe(handler)
    assert consumer.nacked == ["b"]
    assert consumer.acked == []


async def test_fake_consumer_partial_nack() -> None:
    """subscribe() acks successful messages and nacks failed ones."""
    consumer: FakeConsumer[str] = FakeConsumer()
    consumer.feed(["ok", "fail", "ok2"])

    async def handler(msg: str) -> None:
        if msg == "fail":
            raise RuntimeError("oops")

    await consumer.subscribe(handler)
    assert consumer.acked == ["ok", "ok2"]
    assert consumer.nacked == ["fail"]


async def test_fake_consumer_multiple_feeds_accumulate() -> None:
    """Multiple feed() calls accumulate messages in order."""
    consumer: FakeConsumer[str] = FakeConsumer()
    consumer.feed(["first"])
    consumer.feed(["second"])
    received: list[str] = []

    async def handler(msg: str) -> None:
        received.append(msg)

    await consumer.subscribe(handler)
    assert received == ["first", "second"]


def test_fake_consumer_default_capability_is_queue() -> None:
    """FakeConsumer defaults to Capability.QUEUE."""
    consumer: FakeConsumer[str] = FakeConsumer()
    assert consumer.capability == Capability.QUEUE
