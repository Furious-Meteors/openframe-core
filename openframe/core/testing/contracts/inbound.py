"""
openframe/core/testing/contracts/inbound.py
==============================================
UseCaseContractTests, CommandHandlerContractTests, QueryHandlerContractTests
— reusable pytest base classes for the inbound (driving) side of the
hexagon (ADR-006).

Any application service or validation-framework service implementing
:class:`~openframe.core.inbound.usecase.UseCase`,
:class:`~openframe.core.inbound.command.CommandHandler`, or
:class:`~openframe.core.inbound.query.QueryHandler` can prove protocol
conformance by inheriting the matching class here and providing its
required fixture.

Unlike :class:`~openframe.core.testing.contracts.repository.RepositoryContractTests`
(which builds on :class:`~openframe.core.testing.contracts.port.PortContractTests`
for the shared ``BasePort`` identity/lifecycle suite), there is no base
class above these three. ``UseCase``/``CommandHandler``/``QueryHandler``
do not extend ``BasePort`` — they are inbound (driving) contracts, not
outbound ports — so each class stands alone.

No top-level pytest import — this module can be imported without pytest
installed. The test methods use pytest's fixture injection mechanism
through parameter names; pytest is discovered at collection time.

.. stability: beta
   Beta — API may change in minor versions with a deprecation notice.

Dependency order:
    testing/contracts/inbound → inbound

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
"""
from __future__ import annotations

from openframe.core.inbound.context import RequestContext

__all__ = [
    "UseCaseContractTests",
    "CommandHandlerContractTests",
    "QueryHandlerContractTests",
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
