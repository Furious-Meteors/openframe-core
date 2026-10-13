"""
openframe/core/remote/client.py
==================================
RemoteCommandClient, RemoteQueryClient — the outbound counterparts of
openframe.core.inbound's CommandHandler/QueryHandler (openframe-protocol
draft 8, section 5.6; D10).

Structurally identical to CommandHandler/QueryHandler — same
`execute(input, context) -> result` shape — but deliberately a separate
pair of Protocol classes in their own module, not aliases. Two reasons:

1. Direction matters even when the signature doesn't differ. This
   ecosystem's entire organising principle (see openframe-protocol's own
   design history) is driving side vs. driven side, and conflating a
   "something calls into me" contract with a "I call out to something"
   contract under one name would erase exactly the distinction that
   took real design work to land on.
2. `isinstance(x, RemoteQueryClient)` should read as "this is a remote
   call" at the call site, not "this happens to satisfy CommandHandler's
   shape." Structural typing doesn't require the names to differ, but
   the names carry real information a reader relies on.

No BasePort/Identity/Capability involvement, by design — see draft 8
section 4's D10 resolution: there is no dynamic "give me whichever
remote client fills this role" lookup use case (a caller always knows
exactly which service it's calling), so none of the machinery that
justifies Capability-based registry lookup applies here. These are
wired by direct construction in `bootstrap`, the same way `CommandHandler`/
`QueryHandler` themselves are never looked up by Capability.

Dependency order:
    inbound/context  → ports/context
    remote/client    → inbound/context (reuses the same RequestContext —
                        one request's identity threads through both
                        directions of a call it triggers, matching how
                        RequestContext is already shared by inbound).
"""
from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

from openframe.core.inbound.context import RequestContext

__all__ = ["RemoteCommandClient", "RemoteQueryClient"]

TInput = TypeVar("TInput")
TOutput = TypeVar("TOutput")


@runtime_checkable
class RemoteCommandClient(Protocol[TInput]):
    """
    Outbound write-side contract — calls another service to mutate its
    state. The write-side counterpart of
    :class:`~openframe.core.inbound.command.CommandHandler`, for the
    opposite direction.

    Adapters/clients satisfy this protocol structurally — no inheritance
    needed.

    Type parameter:
        TInput: The command type this client sends.

    Runtime check::

        isinstance(client, RemoteCommandClient)       # ✓ works
        isinstance(client, RemoteCommandClient[str])  # ✗ raises TypeError
    """

    async def execute(
        self,
        command: TInput,
        context: RequestContext | None = None,
    ) -> None:
        """
        Send the command to the remote service.

        Args:
            command: The command to send.
            context: Optional request context — a real implementation
                     propagates `context.correlation_id` onward (e.g. as
                     an outgoing `traceparent`), threading one logical
                     request's identity through every service it touches.

        Raises:
            An `AdapterError` subclass on failure — a remote call is, from
            the caller's perspective, exactly as fallible as a database
            call, and should surface through the same exception family
            so callers don't need a separate catch clause for "this
            dependency happens to be another service" versus "this
            dependency happens to be a database."
        """
        ...


@runtime_checkable
class RemoteQueryClient(Protocol[TInput, TOutput]):
    """
    Outbound read-side contract — calls another service and returns its
    result. The read-side counterpart of
    :class:`~openframe.core.inbound.query.QueryHandler`, for the
    opposite direction.

    Type parameters:
        TInput:  The query type this client sends.
        TOutput: The result type this client returns.

    Runtime check::

        isinstance(client, RemoteQueryClient)       # ✓ works
        isinstance(client, RemoteQueryClient[str, int])  # ✗ raises TypeError
    """

    async def execute(
        self,
        query: TInput,
        context: RequestContext | None = None,
    ) -> TOutput:
        """
        Send the query to the remote service and return its result.

        Args:
            query:   The query to send.
            context: Optional request context, propagated onward — see
                     `RemoteCommandClient.execute`'s own docstring.

        Returns:
            The remote service's result.

        Raises:
            An `AdapterError` subclass on failure — see
            `RemoteCommandClient.execute`'s own docstring for why this
            family, not a bespoke one.
        """
        ...
