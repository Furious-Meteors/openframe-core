"""
tests/test_inbound.py
=======================
Tests for openframe.core.inbound — UseCase, CommandHandler, QueryHandler,
RequestContext.
"""
from __future__ import annotations

import dataclasses

import pytest

from openframe.core.contracts import PrincipalContext, TenantContext
from openframe.core.inbound import CommandHandler, QueryHandler, RequestContext, UseCase


# ---------------------------------------------------------------------------
# Helper concrete implementations
# ---------------------------------------------------------------------------


class EchoUseCase:
    """Full implementation of UseCase[str, str]."""

    async def execute(self, command: str, context: RequestContext | None = None) -> str:
        return command


class CreateItemCommandHandler:
    """Full implementation of CommandHandler[dict]."""

    def __init__(self) -> None:
        self.received: list[tuple[dict, RequestContext | None]] = []

    async def execute(self, command: dict, context: RequestContext | None = None) -> None:
        self.received.append((command, context))


class GetItemQueryHandler:
    """Full implementation of QueryHandler[str, dict]."""

    async def execute(self, query: str, context: RequestContext | None = None) -> dict:
        return {"id": query}


class MissingExecute:
    """Has no execute method — must not satisfy any inbound protocol."""


# ---------------------------------------------------------------------------
# UseCase
# ---------------------------------------------------------------------------


def test_use_case_is_runtime_checkable() -> None:
    assert (
        getattr(UseCase, "_is_runtime_protocol", False)
        or hasattr(UseCase, "__protocol_attrs__")
    )


def test_echo_use_case_satisfies_protocol() -> None:
    assert isinstance(EchoUseCase(), UseCase)


def test_missing_execute_fails_use_case_protocol() -> None:
    assert not isinstance(MissingExecute(), UseCase)


async def test_use_case_execute_without_context() -> None:
    use_case = EchoUseCase()
    result = await use_case.execute("hello")
    assert result == "hello"


async def test_use_case_execute_with_context() -> None:
    use_case = EchoUseCase()
    ctx = RequestContext(correlation_id="corr-1")
    result = await use_case.execute("hello", ctx)
    assert result == "hello"


# ---------------------------------------------------------------------------
# CommandHandler
# ---------------------------------------------------------------------------


def test_command_handler_is_runtime_checkable() -> None:
    assert (
        getattr(CommandHandler, "_is_runtime_protocol", False)
        or hasattr(CommandHandler, "__protocol_attrs__")
    )


def test_create_item_handler_satisfies_protocol() -> None:
    assert isinstance(CreateItemCommandHandler(), CommandHandler)


def test_missing_execute_fails_command_handler_protocol() -> None:
    assert not isinstance(MissingExecute(), CommandHandler)


async def test_command_handler_execute_records_context() -> None:
    handler = CreateItemCommandHandler()
    ctx = RequestContext(correlation_id="corr-2")
    await handler.execute({"name": "widget"}, ctx)
    assert handler.received == [({"name": "widget"}, ctx)]


# ---------------------------------------------------------------------------
# QueryHandler
# ---------------------------------------------------------------------------


def test_query_handler_is_runtime_checkable() -> None:
    assert (
        getattr(QueryHandler, "_is_runtime_protocol", False)
        or hasattr(QueryHandler, "__protocol_attrs__")
    )


def test_get_item_handler_satisfies_protocol() -> None:
    assert isinstance(GetItemQueryHandler(), QueryHandler)


def test_missing_execute_fails_query_handler_protocol() -> None:
    assert not isinstance(MissingExecute(), QueryHandler)


async def test_query_handler_execute_returns_result() -> None:
    handler = GetItemQueryHandler()
    result = await handler.execute("item-1")
    assert result == {"id": "item-1"}


# ---------------------------------------------------------------------------
# RequestContext
# ---------------------------------------------------------------------------


def test_request_context_is_frozen_dataclass() -> None:
    ctx = RequestContext(correlation_id="corr-3")
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        ctx.correlation_id = "mutated"  # type: ignore[misc]


def test_request_context_defaults_principal_and_tenant_to_none() -> None:
    ctx = RequestContext(correlation_id="corr-4")
    assert ctx.principal is None
    assert ctx.tenant is None


def test_request_context_threads_principal_and_tenant() -> None:
    principal = PrincipalContext(principal_id="user-1")
    tenant = TenantContext(tenant_id="tenant-1")
    ctx = RequestContext(correlation_id="corr-5", principal=principal, tenant=tenant)
    assert ctx.principal is principal
    assert ctx.tenant is tenant
