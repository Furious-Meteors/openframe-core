"""
openframe/core/ports/producer.py
===================================
Generic message producer port for the OpenFrame ecosystem.

``BaseProducer[T]`` is the structural contract every message-queue publish
adapter implements. Queue adapters (Kafka, SQS, PubSub, Redis Streams)
satisfy this protocol by structural subtyping — no inheritance needed.

Runtime isinstance check::

    isinstance(producer, BaseProducer)       # ✓ works
    isinstance(producer, BaseProducer[str])  # ✗ raises TypeError

Dependency order: this module imports only from Python stdlib typing.
No openframe.core imports.
"""
from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

__all__ = ["BaseProducer"]

T = TypeVar("T")


@runtime_checkable
class BaseProducer(Protocol[T]):
    """
    Generic message producer port.

    Queue adapters implement this protocol structurally — no inheritance
    needed. Any class with matching async method signatures satisfies
    ``BaseProducer``.

    Type parameter ``T`` is the message payload type.

    Runtime check::

        isinstance(producer, BaseProducer)       # ✓ works
        isinstance(producer, BaseProducer[str])  # ✗ raises TypeError

    Methods:
        publish:       Publish a single message to the queue.
        publish_batch: Publish multiple messages in a single call (more
                       efficient than repeated ``publish()`` for bulk loads).
        close:         Flush pending messages and release producer resources.
                       Must be called before process exit.
    """

    async def publish(self, message: T) -> None:
        """
        Publish a single message to the queue.

        Args:
            message: The message payload to publish.

        Raises:
            AdapterConnectionError: If the broker is unreachable.
            AdapterQueryError:      If the publish fails (e.g. topic not found,
                                    serialisation error).
            AdapterTimeoutError:    If the operation exceeds ``operation_timeout``.
        """
        ...

    async def publish_batch(self, messages: list[T]) -> None:
        """
        Publish multiple messages in a single call.

        Implementations should use the backend's native batch API when
        available (e.g. Kafka ``produce`` with flush, SQS ``send_message_batch``).
        Atomicity guarantees depend on the backend.

        Args:
            messages: The list of message payloads to publish.

        Raises:
            AdapterConnectionError: If the broker is unreachable.
            AdapterQueryError:      If any message in the batch fails.
            AdapterTimeoutError:    If the operation exceeds ``operation_timeout``.
        """
        ...

    async def close(self) -> None:
        """
        Flush pending messages and release producer resources.

        Must be called before process exit to ensure all buffered messages
        are delivered. Idempotent — safe to call multiple times.

        Raises:
            AdapterQueryError: If flushing fails and messages may be lost.
        """
        ...
