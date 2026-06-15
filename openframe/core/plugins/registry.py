"""
openframe/core/plugins/registry.py
=====================================
Explicit plugin registry for the OpenFrame platform kernel.

All symbols are **experimental** in v2.0.

.. stability: experimental
   Experimental — API may change or be removed in any version.

Dependency order:
    plugins/contracts → errors/plugin → (no openframe imports)
    plugins/registry  → plugins/contracts + errors/plugin
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from openframe.core.errors.plugin import DuplicatePluginError
from openframe.core.plugins.contracts import (
    OpenFramePlugin,
    PluginContext,
    PluginHealth,
    PluginStatus,
)

if TYPE_CHECKING:
    pass

__all__ = ["PluginRegistry"]

__stability__ = "experimental"

_log = logging.getLogger(__name__)


class PluginRegistry:
    """
    Explicit plugin registry.

    Maintains registration order.  Initializes plugins in registration order.
    Shuts down plugins in reverse registration order (LIFO).
    Does **not** perform automatic package scanning — all registration is
    explicit.  Optional entry-point discovery is deferred to v2.1.

    .. stability: experimental

    Usage::

        registry = PluginRegistry()
        registry.register(PostgresPlugin(settings))
        registry.register(RedisPlugin(settings))
        await registry.initialize_all()
        # ... serve traffic ...
        await registry.shutdown_all()

    Or as an async context manager::

        async with PluginRegistry() as registry:
            registry.register(PostgresPlugin(settings))
            registry.register(RedisPlugin(settings))
            await registry.initialize_all()
            # ... serve traffic ...
        # shutdown_all() called automatically on exit
    """

    def __init__(self) -> None:
        """Initialise an empty registry."""
        self._plugins: list[OpenFramePlugin] = []
        self._by_name: dict[str, OpenFramePlugin] = {}
        self._initialized: list[OpenFramePlugin] = []

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, plugin: OpenFramePlugin) -> None:
        """
        Register a plugin.

        Args:
            plugin: Plugin instance.  Must satisfy
                    :class:`~openframe.core.plugins.contracts.OpenFramePlugin`
                    protocol.

        Raises:
            TypeError:            Object does not satisfy the
                                  ``OpenFramePlugin`` protocol.
            DuplicatePluginError: A plugin with this name is already
                                  registered in this registry.
        """
        if not isinstance(plugin, OpenFramePlugin):
            raise TypeError(
                f"Object {plugin!r} does not satisfy the OpenFramePlugin "
                "protocol.  Ensure it has 'name', 'version', 'capability' "
                "attributes and 'initialize', 'shutdown', 'health' async methods."
            )
        if plugin.name in self._by_name:
            raise DuplicatePluginError(
                f"A plugin named {plugin.name!r} is already registered.  "
                "Plugin names must be unique within a registry.",
                plugin_name=plugin.name,
            )
        self._plugins.append(plugin)
        self._by_name[plugin.name] = plugin
        _log.debug("Plugin registered: name=%r capability=%r", plugin.name, plugin.capability)

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, capability: str) -> OpenFramePlugin:
        """
        Look up the first registered plugin by capability.

        Args:
            capability: Logical role, e.g. ``"persistence"``, ``"cache"``.

        Returns:
            The first registered plugin with the given capability.

        Raises:
            KeyError: No plugin is registered for this capability.
        """
        for plugin in self._plugins:
            if plugin.capability == capability:
                return plugin
        raise KeyError(
            f"No plugin registered for capability {capability!r}.  "
            f"Registered capabilities: "
            f"{sorted({p.capability for p in self._plugins})}"
        )

    def get_all(self, capability: str) -> list[OpenFramePlugin]:
        """
        Return all registered plugins with the given capability.

        Args:
            capability: Logical role to filter by.

        Returns:
            List of matching plugins in registration order.
            Empty list if no plugins match.
        """
        return [p for p in self._plugins if p.capability == capability]

    def list_plugins(self) -> list[PluginHealth]:
        """
        Return a synchronous health snapshot for all registered plugins.

        Returns a ``PluginHealth`` per plugin based on the registry's last
        known lifecycle state.  For a live async health check, use
        :meth:`health_all` instead.

        Returns:
            List of :class:`~openframe.core.plugins.contracts.PluginHealth`
            instances in registration order.
        """
        result: list[PluginHealth] = []
        initialized_names = {p.name for p in self._initialized}
        for plugin in self._plugins:
            if plugin.name in initialized_names:
                status = PluginStatus.INITIALIZED
            else:
                status = PluginStatus.REGISTERED
            result.append(PluginHealth(status=status, message=plugin.name))
        return result

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize_all(self) -> None:
        """
        Initialize all registered plugins in registration order.

        If any plugin fails to initialize the exception propagates
        immediately.  Plugins that were already initialized before the
        failure are shut down in reverse order before the exception is
        re-raised.  This prevents partially-initialized applications from
        serving traffic.

        Raises:
            Exception: The exception raised by the failing plugin's
                       ``initialize()`` method.
        """
        self._initialized = []
        for plugin in self._plugins:
            context = PluginContext(
                config={},
                plugin_name=plugin.name,
            )
            try:
                _log.debug("Initializing plugin: %r", plugin.name)
                await plugin.initialize(context)
                self._initialized.append(plugin)
                _log.debug("Plugin initialized: %r", plugin.name)
            except Exception:
                _log.exception(
                    "Plugin %r failed to initialize — rolling back %d plugin(s)",
                    plugin.name,
                    len(self._initialized),
                )
                for p in reversed(self._initialized):
                    try:
                        await p.shutdown()
                        _log.debug("Rolled back plugin: %r", p.name)
                    except Exception:
                        _log.exception("Error rolling back plugin %r — continuing", p.name)
                raise

    async def shutdown_all(self) -> None:
        """
        Shut down all initialized plugins in reverse initialization order (LIFO).

        Calls ``shutdown()`` on each plugin.  Never raises — logs errors
        and continues so that a single plugin failure does not prevent
        other plugins from shutting down cleanly.
        """
        for plugin in reversed(self._initialized):
            try:
                _log.debug("Shutting down plugin: %r", plugin.name)
                await plugin.shutdown()
                _log.debug("Plugin shut down: %r", plugin.name)
            except Exception:
                _log.exception(
                    "Error shutting down plugin %r — continuing with remaining plugins",
                    plugin.name,
                )
        self._initialized = []

    async def health_all(self) -> dict[str, PluginHealth]:
        """
        Return a live health snapshot for all registered plugins.

        Calls ``plugin.health()`` on each plugin.  If ``health()`` itself
        raises, the result for that plugin is
        ``PluginHealth(status=FAILED, message=str(exc))``.

        Returns:
            Dict mapping plugin name → :class:`~openframe.core.plugins.contracts.PluginHealth`.
        """
        result: dict[str, PluginHealth] = {}
        for plugin in self._plugins:
            try:
                result[plugin.name] = await plugin.health()
            except Exception as exc:
                _log.exception("health() raised for plugin %r", plugin.name)
                result[plugin.name] = PluginHealth(
                    status=PluginStatus.FAILED,
                    message=str(exc),
                )
        return result

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> PluginRegistry:
        """Enter the context manager — returns self without initializing."""
        return self

    async def __aexit__(self, *args: object) -> None:
        """Exit the context manager — calls shutdown_all()."""
        await self.shutdown_all()
