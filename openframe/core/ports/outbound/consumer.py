"""
openframe/core/ports/outbound/consumer.py
============================================
Generic message consumer port for the OpenFrame ecosystem (ADR-006).

``BaseConsumer[T]`` extends
:class:`~openframe.core.ports.port.BasePort` directly — it is
``Identity + Lifecycle`` plus its own domain methods. There is exactly one
lifecycle-aware definition of this port.

Queue adapters (Kafka, SQS, PubSub, Redis Streams) satisfy this protocol by
structural subtyping — no inheritance needed.

Do NOT import ``AsyncIterator`` here — it is not used in this interface.
The consumer uses a push-based handler model (``subscribe`` + callback),
not a pull-based iterator.

Runtime isinstance check::

    isinstance(consumer, BaseConsumer)       # ✓ works
    isinstance(consumer, BaseConsumer[str])  # ✗ raises TypeError

Dependency order:
    ports/port              → ports/identity + ports/lifecycle
    ports/outbound/consumer → ports/port
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol, TypeVar, runtime_checkable

from openframe.core.ports.port import BasePort

__all__ = ["BaseConsumer"]

T = TypeVar("T")


@runtime_checkable
class BaseConsumer(BasePort, Protocol[T]):
    """
    Generic message consumer port. ``BasePort`` (Identity + Lifecycle)
    plus domain-specific subscribe/ack/nack methods.

    Queue adapters implement this protocol structurally — no inheritance
    needed. Any class with matching async method signatures, plus the
    ``BasePort`` members, satisfies ``BaseConsumer``.

    Type parameter ``T`` is the message payload type.

    The consumer uses a push-based handler model:
    - ``subscribe(handler)`` starts consuming; the adapter calls ``handler``
      for each received message.
    - The adapter calls ``ack(message)`` after a successful handler return.
    - The adapter calls ``nack(message)`` after a handler exception.
    - ``close()`` stops consuming and releases resources.

    Runtime check::

        isinstance(consumer, BaseConsumer)       # ✓ works
        isinstance(consumer, BaseConsumer[str])  # ✗ raises TypeError

    Plus, inherited from ``BasePort``: ``name``, ``version``, ``capability``,
    ``initialize``, ``shutdown``, ``health``.
    """

    async def subscribe(
        self,
        handler: Callable[[T], Awaitable[None]],
    ) -> None:
        """
        Start consuming messages and pass each one to ``handler``.

        The adapter calls ``ack`` or ``nack`` based on whether ``handler``
        completes successfully or raises. ``subscribe`` typically runs until
        ``close()`` is called.

        Args:
            handler: Async callable that receives one message at a time.
                     Must complete before the next message is delivered
                     (unless the adapter supports concurrent dispatch —
                     document this in the adapter's own docstring).

        Raises:
            AdapterConnectionError: If the broker is unreachable.
            AdapterConfigurationError: If the subscription config is invalid
                                       (e.g. topic does not exist).
        """
        ...

    async def ack(self, message: T) -> None:
        """
        Acknowledge successful processing of a message.

        Signals to the broker that the message was processed successfully
        and should not be redelivered. Typically called by the adapter
        internally after ``handler`` returns without raising.

        Args:
            message: The message to acknowledge.

        Raises:
            AdapterConnectionError: If the broker is unreachable.
            AdapterQueryError:      If the acknowledgement fails.
        """
        ...

    async def nack(self, message: T) -> None:
        """
        Negatively acknowledge a message, signalling processing failure.

        Signals to the broker that the message was not processed successfully.
        Depending on broker configuration this may requeue, dead-letter, or
        discard the message. Typically called by the adapter internally after
        ``handler`` raises.

        Args:
            message: The message to negatively acknowledge.

        Raises:
            AdapterConnectionError: If the broker is unreachable.
            AdapterQueryError:      If the nack fails.
        """
        ...

    async def close(self) -> None:
        """
        Stop consuming and release consumer resources.

        Stops the subscription loop and releases any held connections or
        offsets. Idempotent — safe to call multiple times.

        Raises:
            AdapterQueryError: If clean shutdown fails.
        """
        ...
