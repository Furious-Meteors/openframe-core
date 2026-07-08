"""
openframe/core/testing/fakes/inbound.py
==========================================
EchoUseCase, SpyCommandHandler, SpyQueryHandler — reusable test doubles
for the inbound (driving) side of the hexagon (ADR-006).

Satisfy :class:`~openframe.core.inbound.usecase.UseCase`,
:class:`~openframe.core.inbound.command.CommandHandler`, and
:class:`~openframe.core.inbound.query.QueryHandler` respectively via
structural subtyping — no inheritance. The inbound mirror of the outbound
fakes (:class:`~openframe.core.testing.fakes.repository.InMemoryRepository`,
:class:`~openframe.core.testing.fakes.producer.FakeProducer`,
:class:`~openframe.core.testing.fakes.consumer.FakeConsumer`). Zero
external dependencies beyond :mod:`openframe.core.inbound.context`.

.. stability: beta
   Beta — API may change in minor versions with a deprecation notice.

Dependency order:
    testing/fakes/inbound → inbound/context
"""
from __future__ import annotations

from typing import Any, Generic, TypeVar

from openframe.core.inbound.context import RequestContext

__all__ = ["EchoUseCase", "SpyCommandHandler", "SpyQueryHandler"]

__stability__ = "beta"

T = TypeVar("T")


class EchoUseCase(Generic[T]):
    """
    In-memory use case for use in tests.

    Records every call in :attr:`calls` and :attr:`contexts`. Returns
    :attr:`response` if one was configured at construction, otherwise
    echoes the ``command`` argument back to the caller (hence the name).
    Raises :attr:`raises` instead of returning, if configured.

    Satisfies :class:`~openframe.core.inbound.usecase.UseCase` via
    structural subtyping — ``isinstance(EchoUseCase(), UseCase)`` returns
    ``True``.

    .. stability: beta

    Usage::

        # Echo behaviour — returns the command unchanged
        use_case = EchoUseCase()
        result = await use_case.execute("hello")
        assert result == "hello"

        # Configured response
        use_case = EchoUseCase(response={"id": "1"})
        result = await use_case.execute("anything")
        assert result == {"id": "1"}

        # Failure simulation
        use_case = EchoUseCase(raises=ValueError("boom"))
        with pytest.raises(ValueError):
            await use_case.execute("anything")

        # Spy assertions
        assert use_case.calls == ["anything"]
    """

    def __init__(
        self,
        *,
        response: Any = None,
        raises: BaseException | None = None,
    ) -> None:
        """
        Initialise an empty echo use case.

        Args:
            response: Value returned by :meth:`execute`. If ``None``
                      (the default), :meth:`execute` returns the
                      ``command`` argument it was called with instead
                      (echo behaviour).
            raises:   If set, :meth:`execute` raises this exception
                      instead of returning.
        """
        self._response = response
        self._raises = raises
        self.calls: list[Any] = []
        self.contexts: list[RequestContext | None] = []

    async def execute(self, command: T, context: RequestContext | None = None) -> Any:
        """
        Record the call and return the configured response.

        Args:
            command: The input driving this execution. Recorded in
                     :attr:`calls`.
            context: Optional request context. Recorded in
                     :attr:`contexts`.

        Returns:
            :attr:`response` if configured, otherwise ``command`` itself.

        Raises:
            Whatever exception was passed as ``raises`` at construction,
            if any.
        """
        self.calls.append(command)
        self.contexts.append(context)
        if self._raises is not None:
            raise self._raises
        return command if self._response is None else self._response


class SpyCommandHandler(Generic[T]):
    """
    In-memory command handler for use in tests.

    Records every call in :attr:`calls` and :attr:`contexts`. Always
    returns ``None`` on success, matching the
    :class:`~openframe.core.inbound.command.CommandHandler` contract.
    Raises :attr:`raises` instead of returning, if configured — the call
    is still recorded before the exception is raised.

    Satisfies :class:`~openframe.core.inbound.command.CommandHandler` via
    structural subtyping — ``isinstance(SpyCommandHandler(), CommandHandler)``
    returns ``True``.

    .. stability: beta

    Usage::

        handler = SpyCommandHandler()
        result = await handler.execute({"name": "widget"})
        assert result is None
        assert handler.call_count == 1

        # Failure simulation
        handler = SpyCommandHandler(raises=RuntimeError("fail"))
        with pytest.raises(RuntimeError):
            await handler.execute({"name": "widget"})
        assert handler.call_count == 1   # call recorded even though it raised
    """

    def __init__(self, *, raises: BaseException | None = None) -> None:
        """
        Initialise an empty spy command handler.

        Args:
            raises: If set, :meth:`execute` raises this exception after
                    recording the call.
        """
        self._raises = raises
        self.calls: list[Any] = []
        self.contexts: list[RequestContext | None] = []

    async def execute(self, command: T, context: RequestContext | None = None) -> None:
        """
        Record the call. Always returns ``None`` on success.

        Args:
            command: The command to execute. Recorded in :attr:`calls`.
            context: Optional request context. Recorded in
                     :attr:`contexts`.

        Raises:
            Whatever exception was passed as ``raises`` at construction,
            if any. The call is recorded before the exception is raised.
        """
        self.calls.append(command)
        self.contexts.append(context)
        if self._raises is not None:
            raise self._raises

    @property
    def call_count(self) -> int:
        """Number of times :meth:`execute` has been called."""
        return len(self.calls)


class SpyQueryHandler(Generic[T]):
    """
    In-memory query handler for use in tests.

    Records every call in :attr:`calls` and :attr:`contexts`. Returns
    :attr:`response` (``None`` by default) on every call. Raises
    :attr:`raises` instead of returning, if configured — the call is
    still recorded before the exception is raised.

    Satisfies :class:`~openframe.core.inbound.query.QueryHandler` via
    structural subtyping — ``isinstance(SpyQueryHandler(), QueryHandler)``
    returns ``True``.

    .. stability: beta

    Usage::

        handler = SpyQueryHandler(response={"id": "item-1"})
        result = await handler.execute("item-1")
        assert result == {"id": "item-1"}
        assert handler.call_count == 1

        # Failure simulation
        handler = SpyQueryHandler(raises=KeyError("missing"))
        with pytest.raises(KeyError):
            await handler.execute("item-1")
        assert handler.call_count == 1   # call recorded even though it raised
    """

    def __init__(
        self,
        *,
        response: Any = None,
        raises: BaseException | None = None,
    ) -> None:
        """
        Initialise an empty spy query handler.

        Args:
            response: Value returned by :meth:`execute` on every call.
            raises:   If set, :meth:`execute` raises this exception after
                      recording the call.
        """
        self._response = response
        self._raises = raises
        self.calls: list[Any] = []
        self.contexts: list[RequestContext | None] = []

    async def execute(self, query: T, context: RequestContext | None = None) -> Any:
        """
        Record the call and return the configured response.

        Args:
            query:   The query to execute. Recorded in :attr:`calls`.
            context: Optional request context. Recorded in
                     :attr:`contexts`.

        Returns:
            :attr:`response`.

        Raises:
            Whatever exception was passed as ``raises`` at construction,
            if any. The call is recorded before the exception is raised.
        """
        self.calls.append(query)
        self.contexts.append(context)
        if self._raises is not None:
            raise self._raises
        return self._response

    @property
    def call_count(self) -> int:
        """Number of times :meth:`execute` has been called."""
        return len(self.calls)
