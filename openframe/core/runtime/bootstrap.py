"""
openframe/core/runtime/bootstrap.py
=====================================
Optional composition root base class for OpenFrame applications.

All symbols are **experimental** in v2.0.

.. stability: experimental
   Experimental — API may change or be removed in any version.

Dependency order:
    plugins/registry → plugins/contracts → errors/plugin
    runtime/bootstrap → plugins/registry
"""
from __future__ import annotations

from openframe.core.plugins.contracts import OpenFramePlugin, PluginHealth
from openframe.core.plugins.registry import PluginRegistry

__all__ = ["ApplicationBootstrap"]

__stability__ = "experimental"


class ApplicationBootstrap:
    """
    Optional composition root base class.

    Manages plugin registration and lifecycle.  Applications that want
    structured startup/shutdown may subclass this.  Applications that
    prefer explicit ``deps.py`` wiring continue to work exactly as before —
    this class is **never** mandatory.

    .. stability: experimental

    Subclass usage::

        class MyServiceBootstrap(ApplicationBootstrap):
            def configure(self) -> None:
                self.register(PostgresPlugin(PostgresSettings()))
                self.register(RedisPlugin(RedisSettings()))

        async with MyServiceBootstrap() as bootstrap:
            repo = bootstrap.get("persistence")
            service = ItemService(repo)
            await serve(service)

    Manual lifecycle usage::

        bootstrap = MyServiceBootstrap()
        bootstrap.configure()
        await bootstrap.start()
        try:
            await serve(...)
        finally:
            await bootstrap.stop()
    """

    def __init__(self) -> None:
        """Initialise bootstrap with an empty plugin registry."""
        self._registry = PluginRegistry()

    def configure(self) -> None:
        """
        Override to register plugins.

        Called automatically by :meth:`start` and :meth:`__aenter__`.
        The default implementation is a no-op — subclasses should override
        and call :meth:`register` for each plugin they need.
        """

    def register(self, plugin: OpenFramePlugin) -> None:
        """
        Register a plugin with the internal registry.

        Delegates to :meth:`~openframe.core.plugins.registry.PluginRegistry.register`.

        Args:
            plugin: Plugin instance satisfying
                    :class:`~openframe.core.plugins.contracts.OpenFramePlugin`.

        Raises:
            TypeError:            Object does not satisfy the plugin protocol.
            DuplicatePluginError: A plugin with this name is already registered.
        """
        self._registry.register(plugin)

    def get(self, capability: str) -> OpenFramePlugin:
        """
        Look up a plugin by capability.

        Only valid after :meth:`start` has been called (i.e. after
        :meth:`configure` and :meth:`~openframe.core.plugins.registry.PluginRegistry.initialize_all`
        have completed).

        Args:
            capability: Logical role, e.g. ``"persistence"``, ``"cache"``.

        Returns:
            The first registered plugin with the given capability.

        Raises:
            KeyError: No plugin is registered for this capability.
        """
        return self._registry.get(capability)

    async def start(self) -> None:
        """
        Configure and initialize all plugins.

        Calls :meth:`configure` then
        :meth:`~openframe.core.plugins.registry.PluginRegistry.initialize_all`.
        If any plugin fails to initialize the exception propagates after
        rolling back already-initialized plugins.
        """
        self.configure()
        await self._registry.initialize_all()

    async def stop(self) -> None:
        """
        Shut down all plugins in reverse initialization order.

        Delegates to
        :meth:`~openframe.core.plugins.registry.PluginRegistry.shutdown_all`.
        Never raises — plugin errors are logged and shutdown continues.
        """
        await self._registry.shutdown_all()

    async def health(self) -> dict[str, PluginHealth]:
        """
        Return live health snapshots for all registered plugins.

        Delegates to
        :meth:`~openframe.core.plugins.registry.PluginRegistry.health_all`.

        Returns:
            Dict mapping plugin name → PluginHealth.
        """
        return await self._registry.health_all()

    async def __aenter__(self) -> ApplicationBootstrap:
        """Enter the context manager — calls :meth:`start`."""
        await self.start()
        return self

    async def __aexit__(self, *args: object) -> None:
        """Exit the context manager — calls :meth:`stop`."""
        await self.stop()
