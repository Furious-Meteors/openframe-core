"""
openframe/core/inbound/usecase.py
====================================
UseCase — the general driving-side contract (ADR-006).

The inbound counterpart to :class:`~openframe.core.contracts.port.BasePort`.
Where a ``BasePort`` is something the application *depends on* (an
outbound adapter), a ``UseCase`` is something that *drives* the
application — invoked by an inbound adapter (an HTTP route, a message
handler, a CLI command) in response to something happening outside the
system.

``CommandHandler`` and ``QueryHandler`` (in ``command.py``/``query.py``)
are the CQRS-flavoured specialisations of this same shape for callers that
want to distinguish reads from writes at the type level; ``UseCase`` is the
general form for callers that don't need that distinction.

Dependency order:
    inbound/context  → contracts/context
    inbound/usecase  → inbound/context
"""
from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

from openframe.core.inbound.context import RequestContext

__all__ = ["UseCase"]

TInput = TypeVar("TInput")
TOutput = TypeVar("TOutput")


@runtime_checkable
class UseCase(Protocol[TInput, TOutput]):
    """
    General-purpose driving-side contract.

    Adapters satisfy this protocol structurally — no inheritance needed.
    Any class with a matching async ``execute`` method satisfies
    ``UseCase``.

    Type parameters:
        TInput:  The input/command type this use case accepts.
        TOutput: The result type this use case returns.

    Runtime check::

        isinstance(handler, UseCase)       # ✓ works
        isinstance(handler, UseCase[str, int])  # ✗ raises TypeError
    """

    async def execute(
        self,
        command: TInput,
        context: RequestContext | None = None,
    ) -> TOutput:
        """
        Execute the use case.

        Args:
            command: The input driving this execution (a command, query,
                     or plain request DTO — the concrete type is up to
                     the implementer).
            context: Optional request context carrying a correlation id
                     and identity information. ``None`` when the caller
                     has no context to propagate (e.g. a unit test).

        Returns:
            The use case's result.
        """
        ...
