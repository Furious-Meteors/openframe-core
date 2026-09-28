"""
openframe/core/runtime/bootstrap.py
=====================================
Recommended composition root for OpenFrame applications (ADR-006).

``ApplicationBootstrap`` is the single recommended starting point for
wiring ports in application code, at three levels of ceremony:

1. **``ApplicationBootstrap.compose(*ports)``** — no subclass needed. The
   default for a service with one or a few ports that don't need per-port
   ``config``/``init_timeout`` or runtime-conditional registration order.
2. **Subclass + ``configure()``** — the standard path once a port needs
   ``config=``, ``init_timeout=``, or registration order that depends on
   something decided at runtime.
3. **``self.registry``** — the escape hatch. Exposes the underlying
   ``PluginRegistry`` directly for the rare customization neither tier
   above covers (e.g. ``get_all()`` for a deliberate multi-port-per-capability
   setup, or ``list_plugins()``), without abandoning ``ApplicationBootstrap``
   and standing up a second, parallel registry to get it.

All three tiers share the same structured ``configure → start → stop``
lifecycle with correct shutdown ordering: ports are shut down first (LIFO),
then the OTel SDK is flushed via ``shutdown_telemetry()``. There is
intentionally no separate ``PluginRegistry``-direct or ``deps.py``+``lru_cache``
"pattern" documented alongside this one — both are what tier 2/3 above look
like when hand-rolled, minus the correct shutdown ordering tier 1-3 give you
for free.

Stable as of v3.3.0 — graduated from experimental after all 7
``openframe-local-validation-framework`` services proved it in
production-shaped code across multiple releases with no breaking change,
and the v3.3.0 ``compose()``/``get_all()``/``registry`` additions landed
as pure additive extensions on top of this contract, confirming the shape
was already right.

.. stability: stable

Dependency order:
    ports             → (apex)
    plugins/registry  → ports + errors/plugin
    runtime/bootstrap → plugins/registry + ports
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from openframe.core.ports import BasePort, Capability, PluginHealth
from openframe.core.plugins.registry import PluginRegistry

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any

__all__ = ["ApplicationBootstrap"]

__stability__ = "stable"


class ApplicationBootstrap:
    """
    Recommended composition root for OpenFrame applications.

    Wraps :class:`~openframe.core.plugins.registry.PluginRegistry` and
    provides a structured ``configure → start → stop`` lifecycle. Subclass
    this and override :meth:`configure` to register ports. Handles correct
    shutdown ordering automatically: ports are shut down first (LIFO), then
    the OTel SDK is flushed via ``shutdown_telemetry()`` so no spans are
    silently dropped at process exit.

    .. stability: stable

    **Tier 1 — no subclass, one or a few ports**::

        async with ApplicationBootstrap.compose(PostgresRepository(settings)) as bootstrap:
            repo = bootstrap.get(Capability.PERSISTENCE)
            service = ItemService(repo)
            await serve(service)

    **Tier 2 — subclass, for per-port config/init_timeout or conditional registration**::

        class MyServiceBootstrap(ApplicationBootstrap):
            def configure(self) -> None:
                self.register(PostgresRepository(settings), config=pg_config)
                self.register(RedisCache(settings), config=redis_config)

        async with MyServiceBootstrap() as bootstrap:
            repo = bootstrap.get(Capability.PERSISTENCE)
            service = ItemService(repo)
            await serve(service)

    **Tier 3 — the registry escape hatch, for what tiers 1-2 don't cover**::

        primary, replica = bootstrap.registry.get_all(Capability.PERSISTENCE)

    **Manual lifecycle usage** (any tier)::

        bootstrap = MyServiceBootstrap()
        await bootstrap.start()   # calls configure() then initialize_all()
        try:
            await serve(...)
        finally:
            await bootstrap.stop()
    """

    def __init__(self, *, default_init_timeout: float | None = None) -> None:
        """
        Initialise bootstrap with an empty plugin registry.

        Args:
            default_init_timeout: Seconds to wait for each port's
                ``initialize()`` in :meth:`start`, unless overridden
                per-port via :meth:`register`. ``None`` (the default)
                applies no timeout — matches pre-existing behaviour.
        """
        self._registry = PluginRegistry(default_init_timeout=default_init_timeout)

    def configure(self) -> None:
        """
        Override to register ports.

        Called automatically by :meth:`start` and :meth:`__aenter__`.
        The default implementation is a no-op — subclasses should override
        and call :meth:`register` for each port they need.
        """

    def register(
        self,
        plugin: BasePort,
        *,
        config: Mapping[str, Any] | None = None,
        init_timeout: float | None = None,
    ) -> None:
        """
        Register a port with the internal registry.

        Delegates to :meth:`~openframe.core.plugins.registry.PluginRegistry.register`.

        Args:
            plugin: Port instance satisfying
                    :class:`~openframe.core.ports.port.BasePort`.
            config: This port's validated configuration, threaded through
                    to its :class:`~openframe.core.ports.health.PluginContext`
                    at initialization time.
            init_timeout: Seconds to wait for this port's ``initialize()``
                    in :meth:`start`, overriding the bootstrap's
                    ``default_init_timeout`` for this port only. ``None``
                    (the default) falls back to that default.

        Raises:
            TypeError:            Object does not satisfy the ``BasePort`` protocol.
            DuplicatePluginError: A port with this name is already registered.
        """
        self._registry.register(plugin, config=config, init_timeout=init_timeout)

    def get(self, capability: Capability) -> BasePort:
        """
        Look up a port by capability.

        Only valid after :meth:`start` has been called (i.e. after
        :meth:`configure` and :meth:`~openframe.core.plugins.registry.PluginRegistry.initialize_all`
        have completed).

        Args:
            capability: Logical role from the
                        :class:`~openframe.core.ports.capability.Capability`
                        taxonomy.

        Returns:
            The single registered port with the given capability.

        Raises:
            KeyError:                 No port is registered for this capability.
            AmbiguousCapabilityError: More than one port is registered for
                                      this capability — use :meth:`get_all`
                                      if that is intended.
        """
        return self._registry.get(capability)

    def get_all(self, capability: Capability) -> list[BasePort]:
        """
        Return all registered ports with the given capability.

        The escape hatch for the deliberate multi-port-per-capability case
        (e.g. a primary + replica persistence pair) that :meth:`get`'s
        strictness rejects. Delegates to
        :meth:`~openframe.core.plugins.registry.PluginRegistry.get_all`.

        Only valid after :meth:`start` has been called.

        Args:
            capability: Logical role from the
                        :class:`~openframe.core.ports.capability.Capability`
                        taxonomy.

        Returns:
            List of matching ports in registration order. Empty list if
            none match.
        """
        return self._registry.get_all(capability)

    @property
    def registry(self) -> PluginRegistry:
        """
        The underlying :class:`~openframe.core.plugins.registry.PluginRegistry`.

        An escape hatch for the rare customization :class:`ApplicationBootstrap`
        doesn't itself expose (e.g. inspecting :meth:`~openframe.core.plugins.registry.PluginRegistry.list_plugins`,
        or building a further layer of composition on top). Prefer the
        methods on this class first — :meth:`register`, :meth:`get`,
        :meth:`get_all`, :meth:`health` — before reaching for the registry
        directly; this property exists so that when you do need to, you
        stay within the same composition root instead of standing up a
        second, parallel ``PluginRegistry``.
        """
        return self._registry

    @classmethod
    def compose(cls, *ports: BasePort) -> ApplicationBootstrap:
        """
        Build an ``ApplicationBootstrap`` for one or more ports with no
        subclass required.

        The zero-ceremony entry point for the common case: a service with
        a handful of ports that need standard config-free initialization
        (settings are typically supplied at the port's own construction
        time — see e.g. ``PostgresRepository(settings)`` — not threaded
        through ``PluginContext.config``). Reach for a subclass with
        :meth:`configure` instead when a port needs per-port ``config``,
        a per-port ``init_timeout``, or registration order that depends on
        runtime conditions.

        Args:
            *ports: One or more port instances, each satisfying
                    :class:`~openframe.core.ports.port.BasePort`. Registered
                    in the order given.

        Returns:
            A ready-to-``start()`` (or use as an async context manager)
            ``ApplicationBootstrap`` instance.

        Usage::

            async with ApplicationBootstrap.compose(PostgresRepository(settings)) as app:
                repo = app.get(Capability.PERSISTENCE)
        """
        composed = cls()
        for port in ports:
            composed.register(port)
        return composed

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
