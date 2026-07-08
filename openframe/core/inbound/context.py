"""
openframe/core/inbound/context.py
====================================
RequestContext — the inbound-side counterpart to
:class:`~openframe.core.ports.health.PluginContext` (ADR-006).

Constructed by inbound adapters — HTTP middleware, message-handler
entrypoints, CLI commands — and passed into a
:class:`~openframe.core.inbound.usecase.UseCase`'s ``execute()``. Carries a
correlation id for cross-service tracing plus the same
``PrincipalContext``/``TenantContext`` identity primitives used on the
outbound side, so a single request's identity threads consistently through
both directions of the hexagon.

Dependency order:
    ports/context   → (no openframe imports)
    inbound/context → ports/context
"""
from __future__ import annotations

from dataclasses import dataclass

from openframe.core.ports.context import PrincipalContext, TenantContext

__all__ = ["RequestContext"]


@dataclass(frozen=True)
class RequestContext:
    """
    Context passed into a use case / command / query handler's ``execute()``.

    Frozen — safe to cache and pass across coroutines.

    Attributes:
        correlation_id: Stable identifier correlating this request across
                         logs, spans, and any downstream messages it
                         produces. Typically propagated from (or generated
                         to seed) a distributed trace id.
        principal:       The authenticated caller, if any. ``None`` for
                          unauthenticated or system-initiated requests.
        tenant:           The tenant this request is scoped to, if any.
                          ``None`` for tenant-agnostic requests.
    """

    correlation_id: str
    principal: PrincipalContext | None = None
    tenant: TenantContext | None = None
