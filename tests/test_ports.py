"""
tests/test_ports.py
=====================
Tests for openframe.core.ports — BaseRepository, BaseProducer, BaseConsumer.

Covers:
- runtime_checkable isinstance checks (positive and negative)
- Classes with all required BasePort (identity + lifecycle) + domain
  async methods satisfy the Protocol
- Classes missing any domain method, or any BasePort member, do NOT
  satisfy the Protocol
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable

import pytest

from openframe.core.contracts import Capability, PluginContext, PluginHealth, PluginStatus
from openframe.core.ports import BaseConsumer, BaseProducer, BaseRepository


# ---------------------------------------------------------------------------
# Helper concrete implementations
# ---------------------------------------------------------------------------


class BasePortMixin:
    """Minimal BasePort (Identity + Lifecycle) implementation shared by helpers."""

    name = "concrete"
    version = "1.0.0"
    capability = Capability.PERSISTENCE

    async def initialize(self, context: PluginContext) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    async def health(self) -> PluginHealth:
        return PluginHealth(status=PluginStatus.READY)


class ConcreteRepository(BasePortMixin):
    """Full implementation of BaseRepository[str]."""

    async def get(self, entity_id: str) -> str | None:
        return None

    async def list(self, limit: int, offset: int) -> tuple[list[str], int]:
        return [], 0

    async def create(self, entity: str) -> str:
        return entity

    async def update(self, entity: str) -> str | None:
        return entity

    async def delete(self, entity_id: str) -> bool:
        return True


class RepositoryMissingDelete(BasePortMixin):
    """Missing the delete method — must NOT satisfy BaseRepository."""

    async def get(self, entity_id: str) -> str | None:
        return None

    async def list(self, limit: int, offset: int) -> tuple[list[str], int]:
        return [], 0

    async def create(self, entity: str) -> str:
        return entity

    async def update(self, entity: str) -> str | None:
        return entity


class RepositoryMissingCreate(BasePortMixin):
    """Missing create — must NOT satisfy BaseRepository."""

    async def get(self, entity_id: str) -> str | None:
        return None

    async def list(self, limit: int, offset: int) -> tuple[list[str], int]:
        return [], 0

    async def update(self, entity: str) -> str | None:
        return entity

    async def delete(self, entity_id: str) -> bool:
        return True


class RepositoryMissingLifecycle:
    """Has all domain methods but no BasePort identity/lifecycle members."""

    async def get(self, entity_id: str) -> str | None:
        return None

    async def list(self, limit: int, offset: int) -> tuple[list[str], int]:
        return [], 0

    async def create(self, entity: str) -> str:
        return entity

    async def update(self, entity: str) -> str | None:
        return entity

    async def delete(self, entity_id: str) -> bool:
        return True


class ConcreteProducer(BasePortMixin):
    """Full implementation of BaseProducer[str]."""

    capability = Capability.QUEUE

    async def publish(self, message: str) -> None:
        pass

    async def publish_batch(self, messages: list[str]) -> None:
        pass

    async def close(self) -> None:
        pass


class ProducerMissingPublishBatch(BasePortMixin):
    """Missing publish_batch — must NOT satisfy BaseProducer."""

    async def publish(self, message: str) -> None:
        pass

    async def close(self) -> None:
        pass


class ConcreteConsumer(BasePortMixin):
    """Full implementation of BaseConsumer[str]."""

    capability = Capability.QUEUE

    async def subscribe(
        self,
        handler: Callable[[str], Awaitable[None]],
    ) -> None:
        pass

    async def ack(self, message: str) -> None:
        pass

    async def nack(self, message: str) -> None:
        pass

    async def close(self) -> None:
        pass


class ConsumerMissingSubscribe(BasePortMixin):
    """Missing subscribe — must NOT satisfy BaseConsumer."""

    async def ack(self, message: str) -> None:
        pass

    async def nack(self, message: str) -> None:
        pass

    async def close(self) -> None:
        pass


class ConsumerMissingNack(BasePortMixin):
    """Missing nack — must NOT satisfy BaseConsumer."""

    async def subscribe(
        self,
        handler: Callable[[str], Awaitable[None]],
    ) -> None:
        pass

    async def ack(self, message: str) -> None:
        pass

    async def close(self) -> None:
        pass


# ---------------------------------------------------------------------------
# BaseRepository
# ---------------------------------------------------------------------------


def test_base_repository_is_runtime_checkable() -> None:
    # _is_runtime_protocol: Python 3.10/3.11
    # __protocol_attrs__:   Python 3.12+
    assert (
        getattr(BaseRepository, "_is_runtime_protocol", False)
        or hasattr(BaseRepository, "__protocol_attrs__")
    )


def test_concrete_repository_satisfies_protocol() -> None:
    repo = ConcreteRepository()
    assert isinstance(repo, BaseRepository)


def test_repository_missing_delete_fails_protocol() -> None:
    repo = RepositoryMissingDelete()
    assert not isinstance(repo, BaseRepository)


def test_repository_missing_create_fails_protocol() -> None:
    repo = RepositoryMissingCreate()
    assert not isinstance(repo, BaseRepository)


def test_repository_missing_lifecycle_fails_protocol() -> None:
    """A class with all CRUD methods but no BasePort members does not satisfy BaseRepository."""
    repo = RepositoryMissingLifecycle()
    assert not isinstance(repo, BaseRepository)


def test_plain_object_does_not_satisfy_repository() -> None:
    assert not isinstance(object(), BaseRepository)


def test_repository_subscripted_isinstance_raises() -> None:
    """isinstance(obj, BaseRepository[str]) is not supported."""
    with pytest.raises(TypeError):
        isinstance(ConcreteRepository(), BaseRepository[str])  # type: ignore[misc]


# ---------------------------------------------------------------------------
# BaseProducer
# ---------------------------------------------------------------------------


def test_base_producer_is_runtime_checkable() -> None:
    assert (
        getattr(BaseProducer, "_is_runtime_protocol", False)
        or hasattr(BaseProducer, "__protocol_attrs__")
    )


def test_concrete_producer_satisfies_protocol() -> None:
    producer = ConcreteProducer()
    assert isinstance(producer, BaseProducer)


def test_producer_missing_publish_batch_fails_protocol() -> None:
    producer = ProducerMissingPublishBatch()
    assert not isinstance(producer, BaseProducer)


def test_plain_object_does_not_satisfy_producer() -> None:
    assert not isinstance(object(), BaseProducer)


# ---------------------------------------------------------------------------
# BaseConsumer
# ---------------------------------------------------------------------------


def test_base_consumer_is_runtime_checkable() -> None:
    assert (
        getattr(BaseConsumer, "_is_runtime_protocol", False)
        or hasattr(BaseConsumer, "__protocol_attrs__")
    )


def test_concrete_consumer_satisfies_protocol() -> None:
    consumer = ConcreteConsumer()
    assert isinstance(consumer, BaseConsumer)


def test_consumer_missing_subscribe_fails_protocol() -> None:
    consumer = ConsumerMissingSubscribe()
    assert not isinstance(consumer, BaseConsumer)


def test_consumer_missing_nack_fails_protocol() -> None:
    consumer = ConsumerMissingNack()
    assert not isinstance(consumer, BaseConsumer)


def test_plain_object_does_not_satisfy_consumer() -> None:
    assert not isinstance(object(), BaseConsumer)
