"""
openframe/core/plugins/registry.py
=====================================
Explicit plugin registry for the OpenFrame platform kernel (ADR-006).

A "plugin" is just a registered
:class:`~openframe.core.contracts.port.BasePort` — there is no separate
plugin protocol. Capability lookups are keyed on the closed
:class:`~openframe.core.contracts.capability.Capability` enum rather than a
raw ``str``.

All symbols are **experimental** in v3.0.

.. stability: experimental
   Experimental — API may change or be removed in any version.

Dependency order:
    contracts        → (apex; no plugins/registry-side imports)
    exceptions       → (lowest layer; no openframe imports)
    telemetry        → exceptions (lower than plugins; record_error seam)
    plugins/registry → contracts + exceptions + telemetry
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from openframe.core.contracts import (
    BasePort,
    Capability,
    PluginContext,
    PluginHealth,
    PluginStatus,
    PrincipalContext,
    TenantContext,
)
from openframe.core.exceptions import AmbiguousCapabilityError, DuplicatePluginError
from openframe.core.telemetry.setup import record_error

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any

__all__ = ["PluginRegistry"]

__stability__ = "experimental"

_log = logging.getLogger(__name__)


class PluginRegistry:
    """
    Explicit plugin registry.

    Maintains registration order. Initializes ports in registration order.
    Shuts down ports in reverse registration order (LIFO).
    Does **not** perform automatic package scanning — all registration is
    explicit. Optional entry-point discovery is deferred to a future minor
    version.

    .. stability: experimental

    Usage::

        registry = PluginRegistry()
        registry.register(PostgresRepository(settings))
        registry.register(RedisCache(settings))
        await registry.initialize_all()
        # ... serve traffic ...
        await registry.shutdown_all()

    Or as an async context manager::

        async with PluginRegistry() as registry:
            registry.register(PostgresRepository(settings))
            registry.register(RedisCache(settings))
            await registry.initialize_all()
            # ... serve traffic ...
        # shutdown_all() called automatically on exit
    """

    def __init__(self) -> None:
        """Initialise an empty registry."""
        self._plugins: list[BasePort] = []
        self._by_name: dict[str, BasePort] = {}
        self._configs: dict[str, Mapping[str, Any]] = {}
        self._initialized: list[BasePort] = []
        self._principal: PrincipalContext | None = None
        self._tenant: TenantContext | None = None

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        plugin: BasePort,
        *,
        config: Mapping[str, Any] | None = None,
    ) -> None:
        """
        Register a port.

        Args:
            plugin: Port instance. Must satisfy
                    :class:`~openframe.core.contracts.port.BasePort`
                    (``name``/``version``/``capability`` attributes and
                    ``initialize``/``shutdown``/``health`` async methods).
            config: This port's validated configuration, threaded through
                    to :class:`~openframe.core.contracts.health.PluginContext`
                    in :meth:`initialize_all`. Defaults to an empty mapping
                    when not provided.

        Raises:
            TypeError:            Object does not satisfy the ``BasePort``
                                  protocol.
            DuplicatePluginError: A port with this name is already
                                  registered in this registry.
        """
        if not isinstance(plugin, BasePort):
            raise TypeError(
                f"Object {plugin!r} does not satisfy the BasePort protocol. "
                "Ensure it has 'name', 'version', 'capability' attributes "
                "and 'initialize', 'shutdown', 'health' async methods."
            )
        if plugin.name in self._by_name:
            raise DuplicatePluginError(
                f"A port named {plugin.name!r} is already registered. "
                "Port names must be unique within a registry.",
                plugin_name=plugin.name,
            )
        self._plugins.append(plugin)
        self._by_name[plugin.name] = plugin
        self._configs[plugin.name] = config if config is not None else {}
        _log.debug("Plugin registered: name=%r capability=%r", plugin.name, plugin.capability)

    def set_context(
        self,
        *,
        principal: PrincipalContext | None = None,
        tenant: TenantContext | None = None,
    ) -> None:
        """
        Set the principal/tenant threaded through every port's
        :class:`~openframe.core.contracts.health.PluginContext` in
        :meth:`initialize_all`.

        Args:
            principal: The principal responsible for this application
                       startup, if any.
            tenant:    The tenant this application instance is scoped to,
                       if any.
        """
        self._principal = principal
        self._tenant = tenant

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, capability: Capability) -> BasePort:
        """
        Look up the single registered port by capability.

        Strict — raises :class:`~openframe.core.exceptions.AmbiguousCapabilityError`
        if more than one port is registered under this capability, rather
        than silently returning the first match. Use :meth:`get_all` when
        multiple ports sharing a capability is the intended configuration
        (e.g. a primary + replica persistence pair).

        Args:
            capability: Logical role from the
                        :class:`~openframe.core.contracts.capability.Capability`
                        taxonomy.

        Returns:
            The single registered port with the given capability.

        Raises:
            KeyError:                 No port is registered for this capability.
            AmbiguousCapabilityError: More than one port is registered for
                                      this capability.
        """
        matches = self.get_all(capability)
        if not matches:
            raise KeyError(
                f"No port registered for capability {capability!r}. "
                f"Registered capabilities: "
                f"{sorted({p.capability for p in self._plugins})}"
            )
        if len(matches) > 1:
            names = [p.name for p in matches]
            raise AmbiguousCapabilityError(
                f"{len(matches)} ports registered for capability {capability!r}: "
                f"{names}. Use get_all() when multiple ports for a capability "
                "is the intended configuration.",
                plugin_name=names[0],
                capability=capability,
                matches=names,
            )
        return matches[0]

    def get_all(self, capability: Capability) -> list[BasePort]:
        """
        Return all registered ports with the given capability.

        Args:
            capability: Logical role to filter by.

        Returns:
            List of matching ports in registration order.
            Empty list if no ports match.
        """
        return [p for p in self._plugins if p.capability == capability]

    def list_plugins(self) -> list[PluginHealth]:
        """
        Return a synchronous health snapshot for all registered ports.

        Returns a ``PluginHealth`` per port based on the registry's last
        known lifecycle state. For a live async health check, use
        :meth:`health_all` instead.

        Returns:
            List of :class:`~openframe.core.contracts.health.PluginHealth`
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
        Initialize all registered ports in registration order.

        Each port receives a
        :class:`~openframe.core.contracts.health.PluginContext` carrying
        its own registered ``config`` (see :meth:`register`) plus the
        registry-wide ``principal``/``tenant`` set via :meth:`set_context`.

        If any port fails to initialize the exception propagates
        immediately. Ports that were already initialized before the
        failure are shut down in reverse order before the exception is
        re-raised. This prevents partially-initialized applications from
        serving traffic.

        Raises:
            Exception: The exception raised by the failing port's
                       ``initialize()`` method.
        """
        self._initialized = []
        for plugin in self._plugins:
            context = PluginContext(
                config=self._configs.get(plugin.name, {}),
                plugin_name=plugin.name,
                principal=self._principal,
                tenant=self._tenant,
            )
            try:
                _log.debug("Initializing plugin: %r", plugin.name)
                await plugin.initialize(context)
                self._initialized.append(plugin)
                _log.debug("Plugin initialized: %r", plugin.name)
            except Exception as exc:
                # Boundary seam: startup failures happen outside any request
                # span. record_error still counts the error and annotates the
                # current (possibly non-recording) span before rollback.
                record_error(exc)
                _log.exception(
                    "Plugin %r failed to initialize — rolling back %d plugin(s)",
                    plugin.name,
                    len(self._initialized),
                )
                for p in reversed(self._initialized):
                    try:
                        await p.shutdown()
                        _log.debug("Rolled back plugin: %r", p.name)
                    except Exception as rollback_exc:
                        record_error(rollback_exc)
                        _log.exception("Error rolling back plugin %r — continuing", p.name)
                raise

    async def shutdown_all(self) -> None:
        """
        Shut down all initialized ports in reverse initialization order (LIFO).

        Calls ``shutdown()`` on each port. Never raises — logs errors
        and continues so that a single port failure does not prevent
        other ports from shutting down cleanly.
        """
        for plugin in reversed(self._initialized):
            try:
                _log.debug("Shutting down plugin: %r", plugin.name)
                await plugin.shutdown()
                _log.debug("Plugin shut down: %r", plugin.name)
            except Exception as exc:
                # Boundary seam: record the shutdown failure but never raise —
                # a single port's failure must not stop the others.
                record_error(exc)
                _log.exception(
                    "Error shutting down plugin %r — continuing with remaining plugins",
                    plugin.name,
                )
        self._initialized = []

    async def health_all(self) -> dict[str, PluginHealth]:
        """
        Return a live health snapshot for all registered ports.

        Calls ``port.health()`` on each port. If ``health()`` itself
        raises, the result for that port is
        ``PluginHealth(status=FAILED, message=str(exc))``.

        Returns:
            Dict mapping port name → :class:`~openframe.core.contracts.health.PluginHealth`.
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
