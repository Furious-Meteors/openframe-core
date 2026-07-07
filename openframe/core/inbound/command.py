"""
openframe/core/inbound/command.py
====================================
CommandHandler — the write-side CQRS specialisation of
:class:`~openframe.core.inbound.usecase.UseCase` (ADR-006).

A command mutates state and does not return a domain result — it returns
``None`` on success or raises. Use ``UseCase`` directly (or
``QueryHandler``) when a return value is needed.

Dependency order:
    inbound/context  → contracts/context
    inbound/command  → inbound/context
"""
from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

from openframe.core.inbound.context import RequestContext

__all__ = ["CommandHandler"]

TInput = TypeVar("TInput")


@runtime_checkable
class CommandHandler(Protocol[TInput]):
    """
    Write-side driving contract — executes a command that mutates state.

    Adapters satisfy this protocol structurally — no inheritance needed.

    Type parameter:
        TInput: The command type this handler accepts.

    Runtime check::

        isinstance(handler, CommandHandler)       # ✓ works
        isinstance(handler, CommandHandler[str])  # ✗ raises TypeError
    """

    async def execute(
        self,
        command: TInput,
        context: RequestContext | None = None,
    ) -> None:
        """
        Execute the command.

        Args:
            command: The command to execute.
            context: Optional request context carrying a correlation id
                     and identity information.

        Raises:
            Any domain or adapter exception the command's execution
            surfaces. Commands do not return a value on success.
        """
        ...
