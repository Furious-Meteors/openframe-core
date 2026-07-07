"""
openframe/core/testing/contracts/producer.py
==============================================
ProducerContractTests — reusable pytest base class (ADR-006).

Every ``openframe-adapters-queue-*`` package must inherit this class and
pass every test.

Builds on :class:`~openframe.core.testing.contracts.port.PortContractTests`
for the full ``BasePort`` (identity + lifecycle) contract, adding
domain-specific publish assertions on top.

No top-level pytest import — this module can be imported without pytest
installed.

.. stability: beta
   Beta — API may change in minor versions with a deprecation notice.

Dependency order:
    testing/contracts/producer → testing/contracts/port + ports + testing/fakes

Subclass usage::

    class TestFakeProducer(ProducerContractTests):
        @pytest.fixture
        def producer(self) -> FakeProducer:
            return FakeProducer()

        @pytest.fixture
        def port(self, producer) -> FakeProducer:
            return producer

    class TestKafkaProducer(ProducerContractTests):
        @pytest.fixture
        async def producer(self, kafka_settings) -> KafkaProducer:
            return KafkaProducer(kafka_settings)

        @pytest.fixture
        def port(self, producer):
            return producer
"""
from __future__ import annotations

from openframe.core.testing.contracts.port import PortContractTests

__all__ = ["ProducerContractTests"]


class ProducerContractTests(PortContractTests):
    """
    Reusable pytest base class for producer contract tests.

    Subclasses must provide two pytest fixtures:

    ``producer``
        A :class:`~openframe.core.ports.BaseProducer` instance to test.

    ``port``
        Typically an alias of ``producer`` (``return producer``) — lets
        the inherited :class:`~openframe.core.testing.contracts.port.PortContractTests`
        identity/lifecycle checks run against the same instance.

    .. stability: beta
    """

    async def test_publish_delivers_message(self, producer) -> None:
        """publish() completes without raising for a valid message."""
        await producer.publish("contract-test-message")

    async def test_publish_batch_delivers_all_messages(self, producer) -> None:
        """publish_batch() completes without raising for a non-empty list."""
        await producer.publish_batch(["batch-msg-1", "batch-msg-2", "batch-msg-3"])

    async def test_close_is_idempotent(self, producer) -> None:
        """close() can be called multiple times without raising."""
        await producer.close()
        await producer.close()

    async def test_satisfies_base_producer_protocol(self, producer) -> None:
        """Producer satisfies BaseProducer via structural subtyping."""
        from openframe.core.ports import BaseProducer

        assert isinstance(producer, BaseProducer), (
            f"{type(producer).__name__} does not satisfy BaseProducer. "
            "Ensure it implements async publish, publish_batch, and close, "
            "plus the BasePort identity/lifecycle members."
        )
