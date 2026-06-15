"""
tests/test_runtime.py
======================
Tests for openframe.core.runtime — ApplicationBootstrap.
"""
from __future__ import annotations

import pytest

from openframe.core.plugins import OpenFramePlugin, PluginContext, PluginHealth, PluginStatus
from openframe.core.runtime import ApplicationBootstrap


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class SimplePlugin:
    """Minimal plugin for bootstrap tests."""

    def __init__(
        self,
        name: str = "simple",
        capability: str = "test",
        *,
        fail_init: bool = False,
    ) -> None:
        self.name = name
        self.version = "1.0.0"
        self.capability = capability
        self._fail_init = fail_init
        self.initialized = False
        self.shutdown_called = False

    async def initialize(self, context: PluginContext) -> None:
        if self._fail_init:
            raise RuntimeError(f"Deliberate init failure: {self.name!r}")
        self.initialized = True

    async def shutdown(self) -> None:
        self.shutdown_called = True

    async def health(self) -> PluginHealth:
        status = PluginStatus.READY if self.initialized else PluginStatus.REGISTERED
        return PluginHealth(status=status, message=self.name)


# ---------------------------------------------------------------------------
# configure() is called on start
# ---------------------------------------------------------------------------


async def test_bootstrap_configure_called_on_start() -> None:
    """start() invokes configure() before initializing plugins."""
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
    """get() returns the registered plugin after start() completes."""
    plugin = SimplePlugin(name="svc", capability="test")

    class MyBootstrap(ApplicationBootstrap):
        def configure(self) -> None:
            self.register(plugin)

    bootstrap = MyBootstrap()
    await bootstrap.start()
    try:
        result = bootstrap.get("test")
        assert result is plugin
        assert isinstance(result, OpenFramePlugin)
    finally:
        await bootstrap.stop()


# ---------------------------------------------------------------------------
# Context manager — normal path
# ---------------------------------------------------------------------------


async def test_bootstrap_context_manager_starts_and_stops() -> None:
    """async-with ApplicationBootstrap starts and stops cleanly."""
    plugin = SimplePlugin(name="cm", capability="test")

    class MyBootstrap(ApplicationBootstrap):
        def configure(self) -> None:
            self.register(plugin)

    async with MyBootstrap() as bootstrap:
        result = bootstrap.get("test")
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
        capability = "test"

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
    """health() returns a dict of PluginHealth keyed by plugin name."""
    plugin = SimplePlugin(name="health-test", capability="observability")

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
    """All registered plugins are initialized and shut down in lifecycle order."""
    p1 = SimplePlugin(name="p1", capability="persistence")
    p2 = SimplePlugin(name="p2", capability="cache")

    class MyBootstrap(ApplicationBootstrap):
        def configure(self) -> None:
            self.register(p1)
            self.register(p2)

    async with MyBootstrap():
        assert p1.initialized is True
        assert p2.initialized is True

    assert p1.shutdown_called is True
    assert p2.shutdown_called is True
