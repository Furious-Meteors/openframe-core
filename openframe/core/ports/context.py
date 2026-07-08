"""
openframe/core/ports/context.py
==================================
Principal and tenant identity primitives (ADR-006).

Frozen dataclasses threaded through both sides of the hexagon:

- Outbound: :class:`~openframe.core.ports.health.PluginContext` carries
  an optional ``principal``/``tenant`` into
  :meth:`~openframe.core.ports.lifecycle.Lifecycle.initialize`.
- Inbound: ``openframe.core.inbound.context.RequestContext`` carries the
  same two types, constructed by inbound adapters (HTTP middleware,
  message-handler entrypoints) and passed into a use case's ``execute()``.

Keeping these two dataclasses free of any other openframe import means
both the outbound (``ports``) and inbound (``inbound``) sides can depend
on them without a cycle.

Dependency order: this module imports only from Python stdlib.
No openframe.core imports.
"""
from __future__ import annotations

from dataclasses import dataclass, field

__all__ = ["PrincipalContext", "TenantContext"]


@dataclass(frozen=True)
class PrincipalContext:
    """
    Identity of the authenticated caller (user, service account, API key).

    Frozen — safe to cache and pass across coroutines and async boundaries.

    Attributes:
        principal_id: Stable unique identifier for the caller
                      (user id, service account id, API key id).
        roles:        Role names granted to the caller. Empty tuple if the
                      caller has no roles or role information is unavailable.
        claims:       Additional verified claims from the auth token/session
                      (e.g. ``{"email": "...", "org": "..."}"``).
    """

    principal_id: str
    roles: tuple[str, ...] = ()
    claims: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class TenantContext:
    """
    Identity of the tenant the current operation is scoped to.

    Frozen — safe to cache and pass across coroutines and async boundaries.

    Attributes:
        tenant_id: Stable unique identifier for the tenant.
        name:      Human-readable tenant name, if known. Empty string when
                   only the identifier is available.
    """

    tenant_id: str
    name: str = ""
