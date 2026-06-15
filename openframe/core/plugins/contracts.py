"""
openframe/core/plugins/contracts.py
=====================================
Plugin protocol and supporting data types for the OpenFrame plugin kernel.

All symbols in this module are **experimental** in v2.0 and will stabilise
in v2.1 or v3.0 based on real usage.

.. stability: experimental
   Experimental — API may change or be removed in any version.

Dependency order:
    errors/plugin → (no openframe imports)
    plugins/contracts → errors/plugin
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Mapping, Protocol, runtime_checkable

__all__ = [
    "PluginStatus",
    "PluginHealth",
    "PluginContext",
    "OpenFramePlugin",
]

__stability__ = "experimental"


class PluginStatus(Enum):
    """
    Lifecycle status values for a plugin.

    Plugins transition through these states during application startup
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
    Health snapshot returned by :meth:`OpenFramePlugin.health`.

    Frozen — instances are safe to cache and pass across coroutines.

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
    Context passed to :meth:`OpenFramePlugin.initialize`.

    Intentionally narrow — plugins cannot look up other plugins from the
    context.  Cross-plugin dependencies must be resolved by the registry
    before ``initialize()`` is called (e.g. by ordering registrations so
    that dependency plugins are registered and initialized first).

    Attributes:
        config:      This plugin's validated configuration as a read-only
                     mapping.  The registry passes an empty mapping when
                     no external configuration is provided.
        plugin_name: The plugin's registered name, as returned by
                     ``plugin.name``.
    """

    config: Mapping[str, Any]
    plugin_name: str


@runtime_checkable
class OpenFramePlugin(Protocol):
    """
    Plugin contract for the OpenFrame ecosystem.

    Every adapter that participates in lifecycle management implements this
    protocol structurally — no inheritance from ``OpenFramePlugin`` is
    required or desired.

    Attributes:
        name:       Unique plugin name within a registry (e.g. "postgres-main").
        version:    Plugin version string (e.g. "1.2.3").
        capability: Logical role (e.g. "persistence", "cache", "queue",
                    "observability"). Used for capability-based lookup via
                    :meth:`~openframe.core.plugins.registry.PluginRegistry.get`.

    .. stability: experimental
    """

    name: str
    version: str
    capability: str

    async def initialize(self, context: PluginContext) -> None:
        """
        Initialize the plugin with its configuration.

        Called once during application startup after all plugins are
        registered.  Must complete before the application serves traffic.

        Args:
            context: Plugin context containing validated configuration and
                     the plugin's registered name.

        Raises:
            AdapterConfigurationError: Configuration is invalid.
            AdapterConnectionError:    Backend is unreachable.
        """
        ...

    async def shutdown(self) -> None:
        """
        Release all resources held by the plugin.

        Called once during graceful shutdown, in reverse initialization order.
        Idempotent — safe to call multiple times.
        Must not raise — implementations should log errors and continue.
        """
        ...

    async def health(self) -> PluginHealth:
        """
        Return the current health snapshot.

        Must not raise — return
        ``PluginHealth(status=PluginStatus.FAILED, message=str(exc))``
        on any exception.
        """
        ...
