"""
openframe/core/inbound/query.py
==================================
QueryHandler — the read-side CQRS specialisation of
:class:`~openframe.core.inbound.usecase.UseCase` (ADR-006).

A query reads state and returns a result without mutating anything. Use
``CommandHandler`` for the write side, or ``UseCase`` directly when the
read/write distinction doesn't matter to the caller.

Dependency order:
    inbound/context → contracts/context
    inbound/query   → inbound/context
"""
from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

from openframe.core.inbound.context import RequestContext

__all__ = ["QueryHandler"]

TInput = TypeVar("TInput")
TOutput = TypeVar("TOutput")


@runtime_checkable
class QueryHandler(Protocol[TInput, TOutput]):
    """
    Read-side driving contract — executes a query and returns a result.

    Adapters satisfy this protocol structurally — no inheritance needed.

    Type parameters:
        TInput:  The query type this handler accepts.
        TOutput: The result type this handler returns.

    Runtime check::

        isinstance(handler, QueryHandler)       # ✓ works
        isinstance(handler, QueryHandler[str, int])  # ✗ raises TypeError
    """

    async def execute(
        self,
        query: TInput,
        context: RequestContext | None = None,
    ) -> TOutput:
        """
        Execute the query and return its result.

        Args:
            query:   The query to execute.
            context: Optional request context carrying a correlation id
                     and identity information.

        Returns:
            The query's result. Must not mutate application state.
        """
        ...
