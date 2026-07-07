"""
openframe/core/contracts/lifecycle.py
========================================
Lifecycle half of the unified BasePort contract (ADR-006).

``Lifecycle`` is the "how is this thing managed" side — initialize, shut
down, report health. Combined with
:class:`~openframe.core.contracts.identity.Identity` (the "what is this
thing" side) it forms :class:`~openframe.core.contracts.port.BasePort`.

``health()`` absorbs the pre-v3 ``HealthCheck.ping()``/``is_ready()`` pair
into one call returning a rich
:class:`~openframe.core.contracts.health.PluginHealth` snapshot.

Dependency order:
    contracts/health    → contracts/context
    contracts/lifecycle → contracts/health
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from openframe.core.contracts.health import PluginContext, PluginHealth

__all__ = ["Lifecycle"]


@runtime_checkable
class Lifecycle(Protocol):
    """
    Lifecycle contract — every registrable port/plugin can be started,
    stopped, and asked about its health.

    Adapters satisfy this protocol structurally — no inheritance from
    ``Lifecycle`` is required or desired.
    """

    async def initialize(self, context: PluginContext) -> None:
        """
        Initialize the port with its configuration.

        Called once during application startup, typically by
        :meth:`~openframe.core.plugins.registry.PluginRegistry.initialize_all`,
        after all ports are registered. Must complete before the
        application serves traffic.

        Args:
            context: Context carrying validated configuration plus optional
                     principal/tenant identity.

        Raises:
            AdapterConfigurationError: Configuration is invalid.
            AdapterConnectionError:    Backend is unreachable.
        """
        ...

    async def shutdown(self) -> None:
        """
        Release all resources held by the port.

        Called once during graceful shutdown, in reverse initialization
        order. Idempotent — safe to call multiple times, including before
        ``initialize()`` has ever been called.
        Must not raise — implementations should log errors and continue.
        """
        ...

    async def health(self) -> PluginHealth:
        """
        Return the current health snapshot.

        The single canonical health primitive — replaces the pre-v3
        ``ping()``/``is_ready()`` pair. Implementations that want to
        distinguish cheap-liveness from full-readiness checks encode that
        distinction in ``PluginStatus``/``PluginHealth.details``.

        Must not raise — return
        ``PluginHealth(status=PluginStatus.FAILED, message=str(exc))``
        on any internal failure.
        """
        ...
