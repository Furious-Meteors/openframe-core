"""
openframe/core/inbound/session.py
====================================
SessionHandler — the long-lived-connection driving-side contract
(ADR-008), sibling to :class:`~openframe.core.inbound.usecase.UseCase`.

``UseCase``/``CommandHandler``/``QueryHandler`` (ADR-006) model one-shot
request/response exchanges: one input in, one output out, done. They do
not fit a long-lived connection (WebSocket, SSE) where a handler may
receive zero or many inbound events and send zero or many outbound
events over its lifetime. ``SessionHandler`` is that shape.

``Session[TOut]`` is deliberately **push-based**, not a pull-based
``AsyncIterator`` return value: ``send()``/``close()`` are available from
inside ``on_open``, ``on_event``, or a background task the handler spawns
at ``on_open`` — e.g. forwarding events from an unrelated source (a Kafka
consumer) into an already-open connection, something a generator can't
express without building an internal queue anyway, at which point the
queue *is* a ``Session`` in disguise.

``on_open`` doubles as the accept/reject point — raising rejects the
session, flowing through the exact same
``openframe.protocol.base.errors.categorize``/``build_envelope`` path
every other inbound contract's failures already do, rather than a
second return-value channel a caller would need a separate check for.

``RequestContext`` is built once per session (at connection/handshake
time), not once per event — a session has one correlation id for its
whole lifetime. This matches ``build_request_context``'s own precondition
(headers are only available once, at handshake time) for every transport
this contract is meant to serve.

Dependency order:
    inbound/context  → ports/context
    inbound/session  → inbound/context
"""
from __future__ import annotations

from enum import Enum
from typing import Protocol, TypeVar, runtime_checkable

from openframe.core.inbound.context import RequestContext

__all__ = ["CloseReason", "Session", "SessionHandler"]

TIn = TypeVar("TIn")
TOut = TypeVar("TOut")


class CloseReason(Enum):
    """
    Why a session ended.

    Closed, transport-neutral set — every `openframe-protocol-*` session
    transport maps its own disconnect/shutdown signal onto one of these
    four values rather than inventing its own vocabulary.
    """

    COMPLETED = "completed"
    """The handler or transport ended the session normally."""

    CLIENT_DISCONNECT = "client_disconnect"
    """The remote end disconnected (socket closed, stream aborted)."""

    SERVER_SHUTDOWN = "server_shutdown"
    """The server is shutting down and is closing open sessions."""

    ERROR = "error"
    """An unhandled exception from `on_open`/`on_event` ended the session."""


@runtime_checkable
class Session(Protocol[TOut]):
    """
    Handle a :class:`SessionHandler` uses to push events to the remote end
    and to end the session.

    Adapters satisfy this protocol structurally — no inheritance needed.
    A concrete implementation (e.g. an SSE or WebSocket session) adapts
    its own wire format in :meth:`send`; the handler never sees that
    format.

    Type parameter:
        TOut: The event type this session sends to the remote end.

    Attributes:
        context: The session's `RequestContext`, built once at
                 connection/handshake time and stable for the session's
                 entire lifetime.
    """

    context: RequestContext

    async def send(self, event: TOut) -> None:
        """
        Send one event to the remote end.

        Raises:
            Implementation-defined if called after :meth:`close` — a
            session that has already closed cannot send further events.
        """
        ...

    async def close(self, reason: CloseReason = CloseReason.COMPLETED) -> None:
        """
        End the session.

        Idempotent — calling :meth:`close` more than once has no
        additional effect beyond the first call.

        Args:
            reason: Why the session is ending. Defaults to
                    `CloseReason.COMPLETED` — the handler-initiated,
                    successful end of the session.
        """
        ...


@runtime_checkable
class SessionHandler(Protocol[TIn, TOut]):
    """
    Long-lived-connection driving-side contract.

    Adapters satisfy this protocol structurally — no inheritance needed.
    Any class with matching async `on_open`/`on_event`/`on_close` methods
    satisfies `SessionHandler`.

    Type parameters:
        TIn:  The inbound event type this handler receives via `on_event`.
        TOut: The outbound event type this handler sends via
              `session.send()`.

    Runtime check::

        isinstance(handler, SessionHandler)          # ✓ works
        isinstance(handler, SessionHandler[str, int]) # ✗ raises TypeError
    """

    async def on_open(self, session: Session[TOut]) -> None:
        """
        Called once when the session opens.

        Returning normally accepts the session. Raising rejects it — the
        exception flows through the same
        `openframe.protocol.base.errors.categorize`/`build_envelope` path
        every other inbound contract's failures do, so a reject looks
        like any other mapped error to the caller, not a special case.

        Args:
            session: The newly opened session. `session.context` carries
                     this session's `RequestContext`, stable for its
                     whole lifetime.
        """
        ...

    async def on_event(self, session: Session[TOut], event: TIn) -> None:
        """
        Called once per inbound event, in arrival order.

        Never called at all for a one-directional transport (e.g. SSE,
        which has no client-to-server events) — this is a valid, expected
        lifecycle for such a handler, not a violation of the contract.

        Args:
            session: The open session this event arrived on.
            event:   The inbound event.
        """
        ...

    async def on_close(self, session: Session[TOut], reason: CloseReason) -> None:
        """
        Called exactly once when the session ends, however it ended —
        normal completion, client disconnect, server shutdown, or an
        unhandled error from `on_open`/`on_event`.

        Args:
            session: The now-closed session.
            reason:  Why the session ended.
        """
        ...
