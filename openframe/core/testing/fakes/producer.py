"""
openframe/core/testing/fakes/producer.py
==========================================
FakeProducer — a reusable test double for message producers.

Satisfies :class:`~openframe.core.ports.BaseProducer` structurally.
Zero external dependencies.

.. stability: beta
   Beta — API may change in minor versions with a deprecation notice.

Dependency order:
    testing/fakes/producer → ports + exceptions
"""
from __future__ import annotations

from typing import Generic, TypeVar

from openframe.core.exceptions import AdapterQueryError

__all__ = ["FakeProducer"]

__stability__ = "beta"

T = TypeVar("T")


class FakeProducer(Generic[T]):
    """
    In-memory producer for use in tests.

    Stores all published messages in :attr:`published`.
    Stores each :meth:`publish_batch` call as a separate entry in
    :attr:`batches`.

    Simulates publish failure via ``fail_on_publish=True``.

    Satisfies :class:`~openframe.core.ports.BaseProducer` via structural
    subtyping — ``isinstance(producer, BaseProducer)`` returns ``True``.

    .. stability: beta

    Usage::

        producer = FakeProducer[str]()
        await producer.publish("hello")
        assert producer.published == ["hello"]

        # Batch
        await producer.publish_batch(["a", "b"])
        assert producer.batches == [["a", "b"]]

        # Failure simulation
        producer = FakeProducer(fail_on_publish=True)
        # raises AdapterQueryError on publish / publish_batch
    """

    def __init__(self, *, fail_on_publish: bool = False) -> None:
        """
        Initialise an empty fake producer.

        Args:
            fail_on_publish: When ``True``, :meth:`publish` and
                             :meth:`publish_batch` raise
                             :class:`~openframe.core.exceptions.AdapterQueryError`.
        """
        self._fail = fail_on_publish
        self.published: list[T] = []
        self.batches: list[list[T]] = []

    # ------------------------------------------------------------------
    # BaseProducer[T] interface
    # ------------------------------------------------------------------

    async def publish(self, message: T) -> None:
        """
        Publish a single message.

        Appends *message* to :attr:`published`.

        Args:
            message: The message payload.

        Raises:
            AdapterQueryError: When ``fail_on_publish=True``.
        """
        if self._fail:
            raise AdapterQueryError(
                "Simulated publish failure",
                adapter="fake",
                operation="publish",
            )
        self.published.append(message)

    async def publish_batch(self, messages: list[T]) -> None:
        """
        Publish multiple messages in a single call.

        Appends each message to :attr:`published` and appends the list to
        :attr:`batches`.

        Args:
            messages: The list of message payloads.

        Raises:
            AdapterQueryError: When ``fail_on_publish=True``.
        """
        if self._fail:
            raise AdapterQueryError(
                "Simulated publish failure",
                adapter="fake",
                operation="publish_batch",
            )
        self.published.extend(messages)
        self.batches.append(list(messages))

    async def close(self) -> None:
        """
        No-op close.

        Idempotent — safe to call multiple times.  The in-memory state is
        preserved so tests can still inspect :attr:`published` after close.
        """

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """
        Clear all recorded messages and batches.

        Resets :attr:`published` and :attr:`batches` to empty lists.
        Does not change the ``fail_on_publish`` configuration.
        """
        self.published.clear()
        self.batches.clear()
