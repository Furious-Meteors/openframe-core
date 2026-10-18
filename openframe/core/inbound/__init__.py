"""
openframe.core.inbound
========================
Driving side of the hexagon (ADR-006).

Where ``openframe.core.ports`` models the outbound (driven) side —
things the application depends on — ``inbound`` models the driving side:
use cases and command/query handlers invoked by inbound adapters (HTTP
routes, message-handler entrypoints, CLI commands).

- :class:`~openframe.core.inbound.usecase.UseCase` — general driving contract.
- :class:`~openframe.core.inbound.command.CommandHandler` — write-side CQRS specialisation.
- :class:`~openframe.core.inbound.query.QueryHandler` — read-side CQRS specialisation.
- :class:`~openframe.core.inbound.session.SessionHandler` — long-lived-connection
  specialisation (ADR-008) for transports where a handler may receive zero or
  many inbound events and send zero or many outbound events over time
  (WebSocket, SSE), via a push-based :class:`~openframe.core.inbound.session.Session`
  handle.
- :class:`~openframe.core.inbound.context.RequestContext` — correlation id
  + optional identity, constructed by inbound adapters and passed into
  ``execute()``.

.. stability: experimental
"""
from __future__ import annotations

from openframe.core.inbound.command import CommandHandler
from openframe.core.inbound.context import RequestContext
from openframe.core.inbound.query import QueryHandler
from openframe.core.inbound.session import CloseReason, Session, SessionHandler
from openframe.core.inbound.usecase import UseCase

__all__ = [
    "UseCase",
    "CommandHandler",
    "QueryHandler",
    "SessionHandler",
    "Session",
    "CloseReason",
    "RequestContext",
]
