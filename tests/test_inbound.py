"""
tests/test_inbound.py
=======================
Tests for openframe.core.inbound — UseCase, CommandHandler, QueryHandler,
SessionHandler, Session, CloseReason, RequestContext.
"""
from __future__ import annotations

import dataclasses

import pytest

from openframe.core.ports import PrincipalContext, TenantContext
from openframe.core.inbound import (
    CloseReason,
    CommandHandler,
    QueryHandler,
    RequestContext,
    Session,
    SessionHandler,
    UseCase,
)


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


class RecordingSession:
    """Full implementation of Session[str] — records sent events and close reason."""

    def __init__(self, *, context: RequestContext) -> None:
        self.context = context
        self.sent: list[str] = []
        self.closed = False
        self.close_reason: CloseReason | None = None

    async def send(self, event: str) -> None:
        if self.closed:
            raise RuntimeError("cannot send on a closed session")
        self.sent.append(event)

    async def close(self, reason: CloseReason = CloseReason.COMPLETED) -> None:
        if self.closed:
            return
        self.closed = True
        self.close_reason = reason


class EchoSessionHandler:
    """Full implementation of SessionHandler[str, str] — echoes events back."""

    def __init__(self, *, reject_with: BaseException | None = None) -> None:
        self._reject_with = reject_with
        self.opened: list[Session] = []
        self.closed: list[tuple[Session, CloseReason]] = []

    async def on_open(self, session: Session) -> None:
        if self._reject_with is not None:
            raise self._reject_with
        self.opened.append(session)

    async def on_event(self, session: Session, event: str) -> None:
        await session.send(event)

    async def on_close(self, session: Session, reason: CloseReason) -> None:
        self.closed.append((session, reason))


class MissingSessionMethods:
    """Has no on_open/on_event/on_close — must not satisfy SessionHandler."""


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
# SessionHandler / Session / CloseReason
# ---------------------------------------------------------------------------


def test_session_handler_is_runtime_checkable() -> None:
    assert (
        getattr(SessionHandler, "_is_runtime_protocol", False)
        or hasattr(SessionHandler, "__protocol_attrs__")
    )


def test_echo_session_handler_satisfies_protocol() -> None:
    assert isinstance(EchoSessionHandler(), SessionHandler)


def test_missing_session_methods_fails_session_handler_protocol() -> None:
    assert not isinstance(MissingSessionMethods(), SessionHandler)


def test_recording_session_satisfies_session_protocol() -> None:
    session = RecordingSession(context=RequestContext(correlation_id="corr-6"))
    assert isinstance(session, Session)


async def test_on_open_accepts_and_records_session() -> None:
    handler = EchoSessionHandler()
    session = RecordingSession(context=RequestContext(correlation_id="corr-7"))
    await handler.on_open(session)
    assert handler.opened == [session]
    assert not session.closed


async def test_on_open_reject_raises() -> None:
    handler = EchoSessionHandler(reject_with=PermissionError("nope"))
    session = RecordingSession(context=RequestContext(correlation_id="corr-8"))
    with pytest.raises(PermissionError):
        await handler.on_open(session)
    assert handler.opened == []


async def test_on_event_sends_through_session() -> None:
    handler = EchoSessionHandler()
    session = RecordingSession(context=RequestContext(correlation_id="corr-9"))
    await handler.on_open(session)
    await handler.on_event(session, "hello")
    await handler.on_event(session, "world")
    assert session.sent == ["hello", "world"]


async def test_on_close_records_reason() -> None:
    handler = EchoSessionHandler()
    session = RecordingSession(context=RequestContext(correlation_id="corr-10"))
    await handler.on_open(session)
    await handler.on_close(session, CloseReason.CLIENT_DISCONNECT)
    assert handler.closed == [(session, CloseReason.CLIENT_DISCONNECT)]


async def test_session_send_after_close_raises() -> None:
    session = RecordingSession(context=RequestContext(correlation_id="corr-11"))
    await session.close()
    with pytest.raises(RuntimeError):
        await session.send("too-late")


async def test_session_close_is_idempotent() -> None:
    session = RecordingSession(context=RequestContext(correlation_id="corr-12"))
    await session.close(CloseReason.COMPLETED)
    await session.close(CloseReason.ERROR)
    assert session.close_reason is CloseReason.COMPLETED


def test_close_reason_values() -> None:
    assert CloseReason.COMPLETED.value == "completed"
    assert CloseReason.CLIENT_DISCONNECT.value == "client_disconnect"
    assert CloseReason.SERVER_SHUTDOWN.value == "server_shutdown"
    assert CloseReason.ERROR.value == "error"


def test_session_context_is_stable_across_lifetime() -> None:
    ctx = RequestContext(correlation_id="corr-13")
    session = RecordingSession(context=ctx)
    assert session.context is ctx


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
