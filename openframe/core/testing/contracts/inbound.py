"""
openframe/core/testing/contracts/inbound.py
==============================================
UseCaseContractTests, CommandHandlerContractTests, QueryHandlerContractTests,
SessionHandlerContractTests — reusable pytest base classes for the inbound
(driving) side of the hexagon (ADR-006, ADR-008).

Any application service or validation-framework service implementing
:class:`~openframe.core.inbound.usecase.UseCase`,
:class:`~openframe.core.inbound.command.CommandHandler`,
:class:`~openframe.core.inbound.query.QueryHandler`, or
:class:`~openframe.core.inbound.session.SessionHandler` can prove protocol
conformance by inheriting the matching class here and providing its
required fixture.

Unlike :class:`~openframe.core.testing.contracts.repository.RepositoryContractTests`
(which builds on :class:`~openframe.core.testing.contracts.port.PortContractTests`
for the shared ``BasePort`` identity/lifecycle suite), there is no base
class above these four. ``UseCase``/``CommandHandler``/``QueryHandler``/
``SessionHandler`` do not extend ``BasePort`` — they are inbound (driving)
contracts, not outbound ports — so each class stands alone.

No top-level pytest import — this module can be imported without pytest
installed. The test methods use pytest's fixture injection mechanism
through parameter names; pytest is discovered at collection time.

.. stability: beta
   Beta — API may change in minor versions with a deprecation notice.

Dependency order:
    testing/contracts/inbound → inbound, testing/fakes/inbound (InMemorySession only)

Subclass usage::

    class TestMyUseCase(UseCaseContractTests):
        @pytest.fixture
        def use_case(self) -> MyUseCase:
            return MyUseCase()

    class TestMyCommandHandler(CommandHandlerContractTests):
        @pytest.fixture
        def command_handler(self) -> MyCommandHandler:
            return MyCommandHandler()

    class TestMyQueryHandler(QueryHandlerContractTests):
        @pytest.fixture
        def query_handler(self) -> MyQueryHandler:
            return MyQueryHandler()

        @pytest.fixture
        def make_query(self):
            def _make() -> str:
                return "item-1"
            return _make

    class TestMySessionHandler(SessionHandlerContractTests):
        @pytest.fixture
        def session_handler(self) -> MySessionHandler:
            return MySessionHandler()
"""
from __future__ import annotations

from openframe.core.inbound.context import RequestContext
from openframe.core.inbound.session import CloseReason

__all__ = [
    "UseCaseContractTests",
    "CommandHandlerContractTests",
    "QueryHandlerContractTests",
    "SessionHandlerContractTests",
]


class UseCaseContractTests:
    """
    Reusable pytest base class for :class:`~openframe.core.inbound.usecase.UseCase`
    contract tests.

    Subclasses must provide one pytest fixture:

    ``use_case``
        A fresh instance satisfying
        :class:`~openframe.core.inbound.usecase.UseCase`.

    Subclasses may optionally override the ``make_command`` method to
    supply a custom command payload; the default is a dict ``{"id": "test"}``.
    Not a pytest fixture — a plain overridable method, following the same
    convention as :meth:`~openframe.core.testing.contracts.lifecycle.LifecycleContractTests._make_context`,
    so this module never needs a top-level pytest import.

    .. stability: beta
    """

    def make_command(self):
        """Build a default command payload — a plain dict. Override to customise."""
        return {"id": "test"}

    async def test_satisfies_use_case_protocol(self, use_case) -> None:
        """use_case satisfies UseCase via structural subtyping."""
        from openframe.core.inbound import UseCase

        assert isinstance(use_case, UseCase), (
            f"{type(use_case).__name__} does not satisfy UseCase. "
            "Ensure it has a matching async 'execute' method."
        )

    async def test_execute_without_context_returns_result(self, use_case) -> None:
        """execute(command) completes without raising, given no context."""
        command = self.make_command()
        await use_case.execute(command)

    async def test_execute_with_context_threads_correlation_id(self, use_case) -> None:
        """execute(command, context) accepts a RequestContext without raising."""
        command = self.make_command()
        context = RequestContext(correlation_id="test-corr-1")
        await use_case.execute(command, context)

    async def test_execute_with_none_context_is_accepted(self, use_case) -> None:
        """execute(command, None) is accepted — context is optional."""
        command = self.make_command()
        await use_case.execute(command, None)


class CommandHandlerContractTests:
    """
    Reusable pytest base class for
    :class:`~openframe.core.inbound.command.CommandHandler` contract tests.

    Subclasses must provide one pytest fixture:

    ``command_handler``
        A fresh instance satisfying
        :class:`~openframe.core.inbound.command.CommandHandler`.

    Subclasses may optionally override the ``make_command`` method to
    supply a custom command payload; the default is a dict ``{"id": "test"}``.
    Not a pytest fixture — a plain overridable method, following the same
    convention as :meth:`~openframe.core.testing.contracts.lifecycle.LifecycleContractTests._make_context`,
    so this module never needs a top-level pytest import.

    .. stability: beta
    """

    def make_command(self):
        """Build a default command payload — a plain dict. Override to customise."""
        return {"id": "test"}

    async def test_satisfies_command_handler_protocol(self, command_handler) -> None:
        """command_handler satisfies CommandHandler via structural subtyping."""
        from openframe.core.inbound import CommandHandler

        assert isinstance(command_handler, CommandHandler), (
            f"{type(command_handler).__name__} does not satisfy CommandHandler. "
            "Ensure it has a matching async 'execute' method."
        )

    async def test_execute_returns_none(self, command_handler) -> None:
        """execute(command) returns None on success — the defining CommandHandler property."""
        command = self.make_command()
        result = await command_handler.execute(command)
        assert result is None

    async def test_execute_with_context_returns_none(self, command_handler) -> None:
        """execute(command, context) returns None — context does not change the return type."""
        command = self.make_command()
        context = RequestContext(correlation_id="test-corr-1")
        result = await command_handler.execute(command, context)
        assert result is None

    async def test_execute_with_none_context_is_accepted(self, command_handler) -> None:
        """execute(command, None) completes without raising and returns None."""
        command = self.make_command()
        result = await command_handler.execute(command, None)
        assert result is None


class QueryHandlerContractTests:
    """
    Reusable pytest base class for
    :class:`~openframe.core.inbound.query.QueryHandler` contract tests.

    Subclasses must provide one pytest fixture:

    ``query_handler``
        A fresh instance satisfying
        :class:`~openframe.core.inbound.query.QueryHandler`, configured
        to return a non-``None`` result.

    Subclasses may optionally override the ``make_query`` method to
    supply a custom query payload; the default is the string
    ``"test-query"``. Not a pytest fixture — a plain overridable method,
    following the same convention as
    :meth:`~openframe.core.testing.contracts.lifecycle.LifecycleContractTests._make_context`,
    so this module never needs a top-level pytest import.

    .. stability: beta
    """

    def make_query(self):
        """Build a default query payload — a plain string. Override to customise."""
        return "test-query"

    async def test_satisfies_query_handler_protocol(self, query_handler) -> None:
        """query_handler satisfies QueryHandler via structural subtyping."""
        from openframe.core.inbound import QueryHandler

        assert isinstance(query_handler, QueryHandler), (
            f"{type(query_handler).__name__} does not satisfy QueryHandler. "
            "Ensure it has a matching async 'execute' method."
        )

    async def test_execute_returns_a_result(self, query_handler) -> None:
        """execute(query) returns a non-None result — distinguishes QueryHandler from CommandHandler."""
        query = self.make_query()
        result = await query_handler.execute(query)
        assert result is not None

    async def test_execute_with_context_returns_result(self, query_handler) -> None:
        """execute(query, context) returns a non-None result — context does not change the return type."""
        query = self.make_query()
        context = RequestContext(correlation_id="test-corr-1")
        result = await query_handler.execute(query, context)
        assert result is not None

    async def test_execute_with_none_context_is_accepted(self, query_handler) -> None:
        """execute(query, None) returns a non-None result — context is optional."""
        query = self.make_query()
        result = await query_handler.execute(query, None)
        assert result is not None


class SessionHandlerContractTests:
    """
    Reusable pytest base class for
    :class:`~openframe.core.inbound.session.SessionHandler` contract tests.

    Subclasses must provide one pytest fixture:

    ``session_handler``
        A fresh instance satisfying
        :class:`~openframe.core.inbound.session.SessionHandler`, configured
        to **accept** sessions (``on_open`` returns normally). Testing the
        reject path (``on_open`` raises) is handler-specific — whatever
        condition causes a given handler to reject is up to that handler,
        not something this generic contract suite can assume — and belongs
        in that handler's own tests, the same way the reject/failure paths
        of ``CommandHandler``/``QueryHandler`` aren't exercised generically
        here either.

    Subclasses may optionally override the ``make_event`` method to supply
    a custom inbound event payload; the default is the string
    ``"test-event"``. Not a pytest fixture — a plain overridable method,
    following the same convention as ``make_command``/``make_query`` above.

    .. stability: beta
    """

    def make_event(self):
        """Build a default inbound event payload — a plain string. Override to customise."""
        return "test-event"

    def _make_session(self):
        """
        Build a fresh, open `InMemorySession` for one test.

        Not a pytest fixture — a plain helper method, so a test that needs
        more than one session in sequence (e.g. the full-lifecycle test
        below) can call it more than once without fixture-scope games.
        """
        from openframe.core.testing.fakes.inbound import InMemorySession

        return InMemorySession(context=RequestContext(correlation_id="test-corr-1"))

    async def test_satisfies_session_handler_protocol(self, session_handler) -> None:
        """session_handler satisfies SessionHandler via structural subtyping."""
        from openframe.core.inbound import SessionHandler

        assert isinstance(session_handler, SessionHandler), (
            f"{type(session_handler).__name__} does not satisfy SessionHandler. "
            "Ensure it has matching async 'on_open'/'on_event'/'on_close' methods."
        )

    async def test_on_open_accepts_without_raising(self, session_handler) -> None:
        """on_open(session) completes without raising for an accepting handler."""
        session = self._make_session()
        await session_handler.on_open(session)
        assert not session.closed, "on_open must not close the session itself — that's on_close's job"

    async def test_on_event_does_not_raise(self, session_handler) -> None:
        """on_event(session, event) completes without raising after on_open."""
        session = self._make_session()
        await session_handler.on_open(session)
        await session_handler.on_event(session, self.make_event())

    async def test_on_close_does_not_raise(self, session_handler) -> None:
        """on_close(session, reason) completes without raising after on_open."""
        session = self._make_session()
        await session_handler.on_open(session)
        await session_handler.on_close(session, CloseReason.COMPLETED)

    async def test_full_lifecycle_runs_without_raising(self, session_handler) -> None:
        """on_open -> on_event -> on_close, in order, completes without raising."""
        session = self._make_session()
        await session_handler.on_open(session)
        await session_handler.on_event(session, self.make_event())
        await session_handler.on_close(session, CloseReason.COMPLETED)
