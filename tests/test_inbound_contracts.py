"""
tests/test_inbound_contracts.py
==================================
Tests for openframe.core.testing inbound fakes and their contract
conformance.

Structure
---------
- ``TestEchoUseCaseContracts``          — passes the full
  :class:`~openframe.core.testing.UseCaseContractTests` suite.
- ``TestSpyCommandHandlerContracts``    — passes the full
  :class:`~openframe.core.testing.CommandHandlerContractTests` suite.
- ``TestSpyQueryHandlerContracts``      — passes the full
  :class:`~openframe.core.testing.QueryHandlerContractTests` suite.
- Standalone functions for fake-specific spy/recording behaviour not
  covered by the contract tests.
"""
from __future__ import annotations

import pytest

from openframe.core.inbound import RequestContext
from openframe.core.testing import (
    CommandHandlerContractTests,
    EchoUseCase,
    QueryHandlerContractTests,
    SpyCommandHandler,
    SpyQueryHandler,
    UseCaseContractTests,
)


# ---------------------------------------------------------------------------
# EchoUseCase — contract conformance
# ---------------------------------------------------------------------------


class TestEchoUseCaseContracts(UseCaseContractTests):
    """EchoUseCase must pass the full UseCaseContractTests suite."""

    @pytest.fixture
    def use_case(self) -> EchoUseCase:
        """Provide a fresh EchoUseCase for each test."""
        return EchoUseCase(response={"result": "ok"})


# ---------------------------------------------------------------------------
# SpyCommandHandler — contract conformance
# ---------------------------------------------------------------------------


class TestSpyCommandHandlerContracts(CommandHandlerContractTests):
    """SpyCommandHandler must pass the full CommandHandlerContractTests suite."""

    @pytest.fixture
    def command_handler(self) -> SpyCommandHandler:
        """Provide a fresh SpyCommandHandler for each test."""
        return SpyCommandHandler()


# ---------------------------------------------------------------------------
# SpyQueryHandler — contract conformance
# ---------------------------------------------------------------------------


class TestSpyQueryHandlerContracts(QueryHandlerContractTests):
    """SpyQueryHandler must pass the full QueryHandlerContractTests suite."""

    @pytest.fixture
    def query_handler(self) -> SpyQueryHandler:
        """Provide a fresh SpyQueryHandler for each test."""
        return SpyQueryHandler(response={"id": "test-query"})


# ---------------------------------------------------------------------------
# EchoUseCase — spy/recording behaviour
# ---------------------------------------------------------------------------


async def test_echo_use_case_records_calls() -> None:
    use_case = EchoUseCase(response={"result": "ok"})
    await use_case.execute("first")
    await use_case.execute("second")
    assert use_case.calls == ["first", "second"]


async def test_echo_use_case_records_contexts() -> None:
    use_case = EchoUseCase(response={"result": "ok"})
    ctx = RequestContext(correlation_id="corr-echo-1")
    await use_case.execute("command", ctx)
    await use_case.execute("no-context")
    assert use_case.contexts == [ctx, None]


async def test_echo_use_case_raises_when_configured() -> None:
    use_case = EchoUseCase(raises=ValueError("boom"))
    with pytest.raises(ValueError, match="boom"):
        await use_case.execute("anything")


async def test_echo_use_case_echoes_command_when_no_response_set() -> None:
    use_case = EchoUseCase()
    result = await use_case.execute("hello")
    assert result == "hello"


# ---------------------------------------------------------------------------
# SpyCommandHandler — spy/recording behaviour
# ---------------------------------------------------------------------------


async def test_spy_command_handler_records_calls() -> None:
    handler = SpyCommandHandler()
    await handler.execute({"name": "widget-1"})
    await handler.execute({"name": "widget-2"})
    assert handler.call_count == 2
    assert handler.calls == [{"name": "widget-1"}, {"name": "widget-2"}]


async def test_spy_command_handler_records_contexts() -> None:
    handler = SpyCommandHandler()
    ctx = RequestContext(correlation_id="corr-cmd-1")
    await handler.execute({"name": "widget"}, ctx)
    assert handler.contexts == [ctx]


async def test_spy_command_handler_raises_when_configured() -> None:
    handler = SpyCommandHandler(raises=RuntimeError("fail"))
    with pytest.raises(RuntimeError, match="fail"):
        await handler.execute({"name": "widget"})
    assert handler.call_count == 1


# ---------------------------------------------------------------------------
# SpyQueryHandler — spy/recording behaviour
# ---------------------------------------------------------------------------


async def test_spy_query_handler_records_calls() -> None:
    handler = SpyQueryHandler(response={"id": "item-1"})
    await handler.execute("item-1")
    await handler.execute("item-2")
    assert handler.call_count == 2
    assert handler.calls == ["item-1", "item-2"]


async def test_spy_query_handler_records_contexts() -> None:
    handler = SpyQueryHandler(response={"id": "item-1"})
    ctx = RequestContext(correlation_id="corr-query-1")
    await handler.execute("item-1", ctx)
    assert handler.contexts == [ctx]


async def test_spy_query_handler_raises_when_configured() -> None:
    handler = SpyQueryHandler(raises=KeyError("missing"))
    with pytest.raises(KeyError):
        await handler.execute("item-1")
    assert handler.call_count == 1


async def test_spy_query_handler_returns_configured_response() -> None:
    handler = SpyQueryHandler(response={"id": "item-1", "name": "widget"})
    result = await handler.execute("item-1")
    assert result == {"id": "item-1", "name": "widget"}
