"""
openframe/core/testing/fakes/consumer.py
==========================================
FakeConsumer — a reusable test double for message consumers.

Satisfies :class:`~openframe.core.ports.BaseConsumer` structurally.
Zero external dependencies.

.. stability: beta
   Beta — API may change in minor versions with a deprecation notice.

Dependency order:
    testing/fakes/consumer → ports
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Generic, TypeVar

__all__ = ["FakeConsumer"]

__stability__ = "beta"

T = TypeVar("T")


class FakeConsumer(Generic[T]):
    """
    In-memory consumer for use in tests.

    Messages are fed via :meth:`feed`.  :meth:`subscribe` processes them
    synchronously by calling the handler for each message in insertion order.

    When a handler returns normally, :meth:`ack` is called automatically
    and the message is appended to :attr:`acked`.
    When a handler raises, :meth:`nack` is called automatically and the
    message is appended to :attr:`nacked`.

    Satisfies :class:`~openframe.core.ports.BaseConsumer` via structural
    subtyping — ``isinstance(consumer, BaseConsumer)`` returns ``True``.

    .. stability: beta

    Usage::

        consumer = FakeConsumer[str]()
        consumer.feed(["msg1", "msg2"])

        acked = []
        async def handler(msg: str) -> None:
            acked.append(msg)

        await consumer.subscribe(handler)
        assert acked == ["msg1", "msg2"]
        assert consumer.acked == ["msg1", "msg2"]
        assert consumer.nacked == []
    """

    def __init__(self) -> None:
        """Initialise an empty fake consumer."""
        self._pending: list[T] = []
        self.acked: list[T] = []
        self.nacked: list[T] = []

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------

    def feed(self, messages: list[T]) -> None:
        """
        Add messages to be delivered on the next :meth:`subscribe` call.

        Multiple ``feed()`` calls accumulate — messages are delivered in
        the order they were fed.

        Args:
            messages: Messages to add to the pending queue.
        """
        self._pending.extend(messages)

    # ------------------------------------------------------------------
    # BaseConsumer[T] interface
    # ------------------------------------------------------------------

    async def subscribe(
        self,
        handler: Callable[[T], Awaitable[None]],
    ) -> None:
        """
        Process all pending messages by calling *handler* for each one.

        Drains the pending queue atomically before processing, so messages
        fed after ``subscribe()`` starts are not processed in this call.

        For each message:
        - On success → :meth:`ack` is called.
        - On any exception from *handler* → :meth:`nack` is called.
          The exception is swallowed so remaining messages continue to be
          processed.

        Args:
            handler: Async callable that receives one message at a time.
        """
        messages = list(self._pending)
        self._pending.clear()
        for message in messages:
            try:
                await handler(message)
                await self.ack(message)
            except Exception:
                await self.nack(message)

    async def ack(self, message: T) -> None:
        """
        Acknowledge successful processing of a message.

        Appends *message* to :attr:`acked`.

        Args:
            message: The message to acknowledge.
        """
        self.acked.append(message)

    async def nack(self, message: T) -> None:
        """
        Negatively acknowledge a message, signalling processing failure.

        Appends *message* to :attr:`nacked`.

        Args:
            message: The message to negatively acknowledge.
        """
        self.nacked.append(message)

    async def close(self) -> None:
        """
        No-op close.

        Idempotent — safe to call multiple times.  Pending messages are
        preserved so tests can inspect state after close.
        """
