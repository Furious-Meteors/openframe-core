"""
openframe/core/ports/health.py
=====================================
Canonical lifecycle status, health snapshot, and initialization context
(ADR-006). This is the ONE home for ``PluginStatus``, ``PluginHealth``, and
``PluginContext`` — they previously lived in ``plugins/contracts.py``
(deleted) and are not duplicated anywhere else.

Dependency order:
    ports/context → (no openframe imports)
    ports/health   → ports/context
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Mapping

from openframe.core.ports.context import PrincipalContext, TenantContext

__all__ = ["PluginStatus", "PluginHealth", "PluginContext"]


class PluginStatus(Enum):
    """
    Lifecycle status values for a port/plugin.

    Instances transition through these states during application startup
    and shutdown. The registry tracks the last known state.
    """

    DISCOVERED = auto()
    REGISTERED = auto()
    CONFIGURED = auto()
    INITIALIZED = auto()
    READY = auto()
    STOPPING = auto()
    STOPPED = auto()
    FAILED = auto()


@dataclass(frozen=True)
class PluginHealth:
    """
    Health snapshot returned by :meth:`~openframe.core.ports.lifecycle.Lifecycle.health`.

    Frozen — instances are safe to cache and pass across coroutines.

    This is the single canonical health primitive in the unified contract
    layer — it replaces the pre-v3 ``HealthCheck.ping()``/``is_ready()``
    pair. Implementations that want to distinguish cheap-liveness from
    full-readiness encode that distinction via ``status``/``details``
    rather than via a second method (e.g.
    ``PluginHealth(status=PluginStatus.READY, details={"ping_ms": 2.1})``).

    Attributes:
        status:  Current lifecycle / health status.
        message: Optional human-readable explanation (empty string by default).
        details: Optional arbitrary key/value pairs for rich diagnostics.
    """

    status: PluginStatus
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PluginContext:
    """
    Context passed to :meth:`~openframe.core.ports.lifecycle.Lifecycle.initialize`.

    Intentionally narrow on cross-port dependencies — a port cannot look up
    other ports from this context. Cross-port dependencies must be resolved
    by the registry before ``initialize()`` is called (e.g. by ordering
    registrations so that dependency ports are registered and initialized
    first).

    Attributes:
        config:      This port's validated configuration as a read-only
                     mapping. The registry passes an empty mapping when no
                     external configuration is provided for this port.
        plugin_name: The port's registered name, as returned by
                     ``port.name``.
        principal:   The authenticated principal responsible for bringing
                     up this port, if any (e.g. the deployer identity in a
                     multi-tenant control plane). ``None`` when not
                     applicable — most application startups have no
                     principal in scope.
        tenant:      The tenant this port instance is scoped to, if any.
                     ``None`` for tenant-agnostic ports (the common case).
    """

    config: Mapping[str, Any]
    plugin_name: str
    principal: PrincipalContext | None = None
    tenant: TenantContext | None = None
