"""
openframe/core/runtime/bootstrap.py
=====================================
Optional composition root base class for OpenFrame applications (ADR-006).

All symbols are **experimental** in v3.0.

.. stability: experimental
   Experimental — API may change or be removed in any version.

Dependency order:
    contracts         → (apex)
    plugins/registry  → contracts + errors/plugin
    runtime/bootstrap → plugins/registry + contracts
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from openframe.core.contracts import BasePort, Capability, PluginHealth
from openframe.core.plugins.registry import PluginRegistry

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any

__all__ = ["ApplicationBootstrap"]

__stability__ = "experimental"


class ApplicationBootstrap:
    """
    Optional composition root base class.

    Manages port registration and lifecycle. Applications that want
    structured startup/shutdown may subclass this. Applications that
    prefer explicit ``deps.py`` wiring continue to work exactly as before —
    this class is **never** mandatory.

    .. stability: experimental

    Subclass usage::

        class MyServiceBootstrap(ApplicationBootstrap):
            def configure(self) -> None:
                self.register(PostgresRepository(settings), config=pg_config)
                self.register(RedisCache(settings), config=redis_config)

        async with MyServiceBootstrap() as bootstrap:
            repo = bootstrap.get(Capability.PERSISTENCE)
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
        Override to register ports.

        Called automatically by :meth:`start` and :meth:`__aenter__`.
        The default implementation is a no-op — subclasses should override
        and call :meth:`register` for each port they need.
        """

    def register(self, plugin: BasePort, *, config: Mapping[str, Any] | None = None) -> None:
        """
        Register a port with the internal registry.

        Delegates to :meth:`~openframe.core.plugins.registry.PluginRegistry.register`.

        Args:
            plugin: Port instance satisfying
                    :class:`~openframe.core.contracts.port.BasePort`.
            config: This port's validated configuration, threaded through
                    to its :class:`~openframe.core.contracts.health.PluginContext`
                    at initialization time.

        Raises:
            TypeError:            Object does not satisfy the ``BasePort`` protocol.
            DuplicatePluginError: A port with this name is already registered.
        """
        self._registry.register(plugin, config=config)

    def get(self, capability: Capability) -> BasePort:
        """
        Look up a port by capability.

        Only valid after :meth:`start` has been called (i.e. after
        :meth:`configure` and :meth:`~openframe.core.plugins.registry.PluginRegistry.initialize_all`
        have completed).

        Args:
            capability: Logical role from the
                        :class:`~openframe.core.contracts.capability.Capability`
                        taxonomy.

        Returns:
            The single registered port with the given capability.

        Raises:
            KeyError:                 No port is registered for this capability.
            AmbiguousCapabilityError: More than one port is registered for
                                      this capability — use the registry's
                                      ``get_all`` directly if that is intended.
        """
        return self._registry.get(capability)

    async def start(self) -> None:
        """
        Configure and initialize all ports.

        Calls :meth:`configure` then
        :meth:`~openframe.core.plugins.registry.PluginRegistry.initialize_all`.
        If any port fails to initialize the exception propagates after
        rolling back already-initialized ports.
        """
        self.configure()
        await self._registry.initialize_all()

    async def stop(self) -> None:
        """
        Shut down all ports then flush and shut down the OTel SDK.

        Port shutdown delegates to
        :meth:`~openframe.core.plugins.registry.PluginRegistry.shutdown_all`.
        Telemetry shutdown flushes the ``BatchSpanProcessor`` queue so that
        spans recorded during the current invocation are not silently dropped
        at process exit.

        Never raises — both port and telemetry errors are logged and shutdown
        continues so that a failing port does not prevent the span flush.
        """
        await self._registry.shutdown_all()
        from openframe.core.telemetry import shutdown_telemetry  # lazy — telemetry is optional
        shutdown_telemetry()

    async def health(self) -> dict[str, PluginHealth]:
        """
        Return live health snapshots for all registered ports.

        Delegates to
        :meth:`~openframe.core.plugins.registry.PluginRegistry.health_all`.

        Returns:
            Dict mapping port name → PluginHealth.
        """
        return await self._registry.health_all()

    async def __aenter__(self) -> ApplicationBootstrap:
        """Enter the context manager — calls :meth:`start`."""
        await self.start()
        return self

    async def __aexit__(self, *args: object) -> None:
        """Exit the context manager — calls :meth:`stop`."""
        await self.stop()
