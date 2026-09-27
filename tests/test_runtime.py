"""
tests/test_runtime.py
======================
Tests for openframe.core.runtime — ApplicationBootstrap.
"""
from __future__ import annotations

import asyncio

import pytest

from openframe.core.ports import BasePort, Capability, PluginContext, PluginHealth, PluginStatus
from openframe.core.runtime import ApplicationBootstrap


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class SimplePlugin:
    """Minimal port for bootstrap tests."""

    def __init__(
        self,
        name: str = "simple",
        capability: Capability = Capability.CACHE,
        *,
        fail_init: bool = False,
        init_delay: float = 0.0,
    ) -> None:
        self.name = name
        self.version = "1.0.0"
        self.capability = capability
        self._fail_init = fail_init
        self._init_delay = init_delay
        self.initialized = False
        self.shutdown_called = False
        self.received_context: PluginContext | None = None

    async def initialize(self, context: PluginContext) -> None:
        if self._init_delay:
            await asyncio.sleep(self._init_delay)
        if self._fail_init:
            raise RuntimeError(f"Deliberate init failure: {self.name!r}")
        self.initialized = True
        self.received_context = context

    async def shutdown(self) -> None:
        self.shutdown_called = True

    async def health(self) -> PluginHealth:
        status = PluginStatus.READY if self.initialized else PluginStatus.REGISTERED
        return PluginHealth(status=status, message=self.name)


# ---------------------------------------------------------------------------
# configure() is called on start
# ---------------------------------------------------------------------------


async def test_bootstrap_configure_called_on_start() -> None:
    """start() invokes configure() before initializing ports."""
    configure_calls: list[bool] = []

    class MyBootstrap(ApplicationBootstrap):
        def configure(self) -> None:
            configure_calls.append(True)

    bootstrap = MyBootstrap()
    await bootstrap.start()
    await bootstrap.stop()

    assert configure_calls == [True]


# ---------------------------------------------------------------------------
# get() after start
# ---------------------------------------------------------------------------


async def test_bootstrap_get_returns_plugin_after_start() -> None:
    """get() returns the registered port after start() completes."""
    plugin = SimplePlugin(name="svc", capability=Capability.CACHE)

    class MyBootstrap(ApplicationBootstrap):
        def configure(self) -> None:
            self.register(plugin)

    bootstrap = MyBootstrap()
    await bootstrap.start()
    try:
        result = bootstrap.get(Capability.CACHE)
        assert result is plugin
        assert isinstance(result, BasePort)
    finally:
        await bootstrap.stop()


async def test_bootstrap_register_threads_config() -> None:
    """register(config=...) threads the config through to PluginContext."""
    plugin = SimplePlugin(name="configured", capability=Capability.PERSISTENCE)

    class MyBootstrap(ApplicationBootstrap):
        def configure(self) -> None:
            self.register(plugin, config={"dsn": "postgres://localhost"})

    async with MyBootstrap():
        assert plugin.received_context.config == {"dsn": "postgres://localhost"}


# ---------------------------------------------------------------------------
# Context manager — normal path
# ---------------------------------------------------------------------------


async def test_bootstrap_context_manager_starts_and_stops() -> None:
    """async-with ApplicationBootstrap starts and stops cleanly."""
    plugin = SimplePlugin(name="cm", capability=Capability.CACHE)

    class MyBootstrap(ApplicationBootstrap):
        def configure(self) -> None:
            self.register(plugin)

    async with MyBootstrap() as bootstrap:
        result = bootstrap.get(Capability.CACHE)
        assert result is plugin
        assert plugin.initialized is True

    assert plugin.shutdown_called is True


# ---------------------------------------------------------------------------
# Context manager — exception in body
# ---------------------------------------------------------------------------


async def test_bootstrap_stop_called_on_exception() -> None:
    """stop() is called even when the context manager body raises."""
    shutdown_tracker: list[bool] = []

    class TrackingPlugin:
        name = "tracker"
        version = "1.0.0"
        capability = Capability.CACHE

        async def initialize(self, context: PluginContext) -> None:
            pass

        async def shutdown(self) -> None:
            shutdown_tracker.append(True)

        async def health(self) -> PluginHealth:
            return PluginHealth(status=PluginStatus.READY)

    class MyBootstrap(ApplicationBootstrap):
        def configure(self) -> None:
            self.register(TrackingPlugin())

    with pytest.raises(ValueError, match="deliberate error"):
        async with MyBootstrap():
            raise ValueError("deliberate error")

    assert shutdown_tracker == [True]


# ---------------------------------------------------------------------------
# health() delegates to registry
# ---------------------------------------------------------------------------


async def test_bootstrap_health_delegates_to_registry() -> None:
    """health() returns a dict of PluginHealth keyed by port name."""
    plugin = SimplePlugin(name="health-test", capability=Capability.TRANSPORT)

    class MyBootstrap(ApplicationBootstrap):
        def configure(self) -> None:
            self.register(plugin)

    async with MyBootstrap() as bootstrap:
        health = await bootstrap.health()

    assert "health-test" in health
    assert isinstance(health["health-test"], PluginHealth)
    assert health["health-test"].status == PluginStatus.READY


# ---------------------------------------------------------------------------
# default configure() is a no-op
# ---------------------------------------------------------------------------


async def test_bootstrap_default_configure_is_noop() -> None:
    """ApplicationBootstrap.configure() is a no-op when not overridden."""
    bootstrap = ApplicationBootstrap()
    await bootstrap.start()  # should not raise
    await bootstrap.stop()


# ---------------------------------------------------------------------------
# multiple plugins
# ---------------------------------------------------------------------------


async def test_bootstrap_multiple_plugins_all_started() -> None:
    """All registered ports are initialized and shut down in lifecycle order."""
    p1 = SimplePlugin(name="p1", capability=Capability.PERSISTENCE)
    p2 = SimplePlugin(name="p2", capability=Capability.CACHE)

    class MyBootstrap(ApplicationBootstrap):
        def configure(self) -> None:
            self.register(p1)
            self.register(p2)

    async with MyBootstrap():
        assert p1.initialized is True
        assert p2.initialized is True

    assert p1.shutdown_called is True
    assert p2.shutdown_called is True


# ---------------------------------------------------------------------------
# Init timeout pass-through
# ---------------------------------------------------------------------------


async def test_bootstrap_default_init_timeout_raises_timeout_error() -> None:
    """
    ApplicationBootstrap(default_init_timeout=...) threads through to the
    underlying PluginRegistry — a slow port's initialize() times out.
    """
    plugin = SimplePlugin(init_delay=1.0)

    class MyBootstrap(ApplicationBootstrap):
        def configure(self) -> None:
            self.register(plugin)

    bootstrap = MyBootstrap(default_init_timeout=0.01)
    with pytest.raises(TimeoutError):
        await bootstrap.start()

    assert plugin.initialized is False


async def test_bootstrap_register_per_port_init_timeout_overrides_default() -> None:
    """
    register(init_timeout=...) on ApplicationBootstrap overrides the
    bootstrap-wide default for that one port, mirroring PluginRegistry.
    """
    plugin = SimplePlugin(init_delay=0.05)

    class MyBootstrap(ApplicationBootstrap):
        def configure(self) -> None:
            self.register(plugin, init_timeout=1.0)

    bootstrap = MyBootstrap(default_init_timeout=0.01)
    await bootstrap.start()

    assert plugin.initialized is True


# ---------------------------------------------------------------------------
# compose() — zero-ceremony tier
# ---------------------------------------------------------------------------


async def test_compose_registers_and_starts_single_port() -> None:
    """compose() with one port needs no subclass and works end to end."""
    plugin = SimplePlugin()

    async with ApplicationBootstrap.compose(plugin) as bootstrap:
        assert plugin.initialized is True
        assert bootstrap.get(Capability.CACHE) is plugin

    assert plugin.shutdown_called is True


async def test_compose_registers_multiple_ports_in_order() -> None:
    """compose() accepts several ports, registered in the order given."""
    p1 = SimplePlugin(name="p1", capability=Capability.PERSISTENCE)
    p2 = SimplePlugin(name="p2", capability=Capability.CACHE)

    async with ApplicationBootstrap.compose(p1, p2) as bootstrap:
        assert p1.initialized is True
        assert p2.initialized is True
        assert bootstrap.get(Capability.PERSISTENCE) is p1
        assert bootstrap.get(Capability.CACHE) is p2

    assert p1.shutdown_called is True
    assert p2.shutdown_called is True


async def test_compose_returns_plain_application_bootstrap() -> None:
    """compose() is a classmethod on ApplicationBootstrap itself, not a subclass."""
    bootstrap = ApplicationBootstrap.compose(SimplePlugin())
    assert isinstance(bootstrap, ApplicationBootstrap)
    assert type(bootstrap) is ApplicationBootstrap


# ---------------------------------------------------------------------------
# get_all() — multi-port-per-capability tier
# ---------------------------------------------------------------------------


async def test_bootstrap_get_all_returns_every_matching_port() -> None:
    """get_all() on ApplicationBootstrap mirrors PluginRegistry.get_all()."""
    primary = SimplePlugin(name="primary", capability=Capability.PERSISTENCE)
    replica = SimplePlugin(name="replica", capability=Capability.PERSISTENCE)

    async with ApplicationBootstrap.compose(primary, replica) as bootstrap:
        matches = bootstrap.get_all(Capability.PERSISTENCE)
        assert matches == [primary, replica]

        # get() is still strict — raises when more than one port matches
        with pytest.raises(Exception):
            bootstrap.get(Capability.PERSISTENCE)


async def test_bootstrap_get_all_empty_for_unregistered_capability() -> None:
    """get_all() returns an empty list, not an error, when nothing matches."""
    async with ApplicationBootstrap.compose(SimplePlugin()) as bootstrap:
        assert bootstrap.get_all(Capability.QUEUE) == []


# ---------------------------------------------------------------------------
# registry property — escape hatch tier
# ---------------------------------------------------------------------------


async def test_bootstrap_registry_property_exposes_underlying_registry() -> None:
    """
    The registry property gives direct access to the underlying
    PluginRegistry, e.g. for list_plugins() that ApplicationBootstrap
    doesn't itself wrap.
    """
    plugin = SimplePlugin()

    async with ApplicationBootstrap.compose(plugin) as bootstrap:
        snapshots = bootstrap.registry.list_plugins()
        assert len(snapshots) == 1
        assert snapshots[0].message == plugin.name

    # Same underlying registry the bootstrap itself delegates to
    assert bootstrap.get_all(Capability.CACHE) == bootstrap.registry.get_all(Capability.CACHE)
