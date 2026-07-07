"""
openframe/core/testing/contracts/consumer.py
==============================================
ConsumerContractTests — reusable pytest base class (ADR-006).

Every ``openframe-adapters-queue-*`` package must inherit this class and
pass every test.

Builds on :class:`~openframe.core.testing.contracts.port.PortContractTests`
for the full ``BasePort`` (identity + lifecycle) contract, adding
domain-specific subscribe/ack/nack assertions on top.

No top-level pytest import — this module can be imported without pytest
installed.

The ``consumer`` fixture must return a consumer that has at least one message
already queued and ready to be delivered when ``subscribe()`` is called.
For :class:`~openframe.core.testing.fakes.FakeConsumer`, the fixture should
call ``consumer.feed([...])`` before returning the consumer instance.

.. stability: beta
   Beta — API may change in minor versions with a deprecation notice.

Dependency order:
    testing/contracts/consumer → testing/contracts/port + ports + testing/fakes

Subclass usage::

    class TestFakeConsumer(ConsumerContractTests):
        @pytest.fixture
        def consumer(self) -> FakeConsumer:
            c = FakeConsumer()
            c.feed(["msg1", "msg2"])
            return c

        @pytest.fixture
        def port(self, consumer) -> FakeConsumer:
            return consumer

    class TestKafkaConsumer(ConsumerContractTests):
        @pytest.fixture
        async def consumer(self, kafka_settings, pre_published_messages):
            # pre_published_messages fixture publishes test messages first
            return KafkaConsumer(kafka_settings)

        @pytest.fixture
        def port(self, consumer):
            return consumer
"""
from __future__ import annotations

from openframe.core.testing.contracts.port import PortContractTests

__all__ = ["ConsumerContractTests"]


class ConsumerContractTests(PortContractTests):
    """
    Reusable pytest base class for consumer contract tests.

    Subclasses must provide two pytest fixtures:

    ``consumer``
        A :class:`~openframe.core.ports.BaseConsumer` instance that has
        at least one message ready for delivery when ``subscribe()`` is
        called.

    ``port``
        Typically an alias of ``consumer`` (``return consumer``) — lets
        the inherited :class:`~openframe.core.testing.contracts.port.PortContractTests`
        identity/lifecycle checks run against the same instance.

    .. stability: beta
    """

    async def test_subscribe_delivers_messages_to_handler(self, consumer) -> None:
        """subscribe() calls the handler for every pending message."""
        received: list[object] = []

        async def handler(msg: object) -> None:
            received.append(msg)

        await consumer.subscribe(handler)
        assert len(received) > 0, (
            "subscribe() did not deliver any messages.  "
            "Ensure the 'consumer' fixture pre-seeds messages via feed() "
            "or the backend equivalent."
        )

    async def test_ack_called_on_handler_success(self, consumer) -> None:
        """When the handler succeeds, the message is acknowledged."""
        received: list[object] = []

        async def handler(msg: object) -> None:
            received.append(msg)

        await consumer.subscribe(handler)
        # For consumers that track acks (e.g. FakeConsumer), verify all
        # received messages were acknowledged.
        if hasattr(consumer, "acked"):
            assert len(consumer.acked) == len(received), (
                f"Expected {len(received)} acked messages, "
                f"got {len(consumer.acked)}."
            )

    async def test_nack_called_on_handler_failure(self, consumer) -> None:
        """When the handler raises, the message is negatively acknowledged."""

        async def failing_handler(msg: object) -> None:
            raise ValueError(f"deliberate failure for {msg!r}")

        await consumer.subscribe(failing_handler)
        # For consumers that track nacks (e.g. FakeConsumer), verify at
        # least one message was nacked.
        if hasattr(consumer, "nacked"):
            assert len(consumer.nacked) > 0, (
                "Expected at least one nacked message after handler failure."
            )

    async def test_close_is_idempotent(self, consumer) -> None:
        """close() can be called multiple times without raising."""
        await consumer.close()
        await consumer.close()

    async def test_satisfies_base_consumer_protocol(self, consumer) -> None:
        """Consumer satisfies BaseConsumer via structural subtyping."""
        from openframe.core.ports import BaseConsumer

        assert isinstance(consumer, BaseConsumer), (
            f"{type(consumer).__name__} does not satisfy BaseConsumer. "
            "Ensure it implements async subscribe, ack, nack, and close, "
            "plus the BasePort identity/lifecycle members."
        )
