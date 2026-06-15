"""
tests/test_plugins.py
======================
Tests for openframe.core.plugins — PluginRegistry, contracts, and error types.
"""
from __future__ import annotations

import dataclasses

import pytest

from openframe.core.errors import DuplicatePluginError
from openframe.core.plugins import (
    OpenFramePlugin,
    PluginContext,
    PluginHealth,
    PluginRegistry,
    PluginStatus,
)


# ---------------------------------------------------------------------------
# Test fixtures / helpers
# ---------------------------------------------------------------------------


class DummyPlugin:
    """Minimal plugin that satisfies OpenFramePlugin structurally."""

    def __init__(
        self,
        name: str = "dummy",
        capability: str = "test",
        *,
        fail_init: bool = False,
        fail_shutdown: bool = False,
    ) -> None:
        self.name = name
        self.version = "1.0.0"
        self.capability = capability
        self._fail_init = fail_init
        self._fail_shutdown = fail_shutdown
        self.initialized = False
        self.shutdown_called = False
        self.received_context: PluginContext | None = None

    async def initialize(self, context: PluginContext) -> None:
        if self._fail_init:
            raise RuntimeError(f"Deliberate init failure in {self.name!r}")
        self.initialized = True
        self.received_context = context

    async def shutdown(self) -> None:
        if self._fail_shutdown:
            raise RuntimeError(f"Deliberate shutdown failure in {self.name!r}")
        self.shutdown_called = True

    async def health(self) -> PluginHealth:
        status = PluginStatus.READY if self.initialized else PluginStatus.REGISTERED
        return PluginHealth(status=status, message=self.name)


# ---------------------------------------------------------------------------
# Registration tests
# ---------------------------------------------------------------------------


def test_plugin_registry_registers_plugin() -> None:
    """register() accepts a valid plugin and adds it to the registry."""
    registry = PluginRegistry()
    plugin = DummyPlugin(name="p1")
    registry.register(plugin)
    assert registry.get("test") is plugin


def test_plugin_registry_get_by_capability() -> None:
    """get() returns the first plugin registered with the given capability."""
    registry = PluginRegistry()
    p1 = DummyPlugin(name="p1", capability="persistence")
    p2 = DummyPlugin(name="p2", capability="cache")
    registry.register(p1)
    registry.register(p2)
    assert registry.get("persistence") is p1
    assert registry.get("cache") is p2


def test_plugin_registry_raises_on_duplicate_name() -> None:
    """register() raises DuplicatePluginError for a second plugin with the same name."""
    registry = PluginRegistry()
    registry.register(DummyPlugin(name="dup"))
    with pytest.raises(DuplicatePluginError):
        registry.register(DummyPlugin(name="dup"))


def test_plugin_registry_raises_on_unknown_capability() -> None:
    """get() raises KeyError when no plugin is registered for the capability."""
    registry = PluginRegistry()
    registry.register(DummyPlugin(name="p1", capability="persistence"))
    with pytest.raises(KeyError):
        registry.get("cache")


def test_plugin_registry_raises_on_non_plugin() -> None:
    """register() raises TypeError for objects that do not satisfy OpenFramePlugin."""
    registry = PluginRegistry()
    with pytest.raises(TypeError):
        registry.register("not-a-plugin")  # type: ignore[arg-type]

    with pytest.raises(TypeError):
        registry.register(42)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Lifecycle tests
# ---------------------------------------------------------------------------


async def test_plugin_registry_initialize_all_calls_initialize() -> None:
    """initialize_all() calls initialize() on every registered plugin."""
    registry = PluginRegistry()
    p1 = DummyPlugin(name="p1")
    p2 = DummyPlugin(name="p2")
    registry.register(p1)
    registry.register(p2)
    await registry.initialize_all()
    assert p1.initialized is True
    assert p2.initialized is True


async def test_plugin_registry_initialize_passes_context() -> None:
    """initialize_all() passes a PluginContext with the plugin's name."""
    registry = PluginRegistry()
    plugin = DummyPlugin(name="ctx-test")
    registry.register(plugin)
    await registry.initialize_all()
    assert plugin.received_context is not None
    assert plugin.received_context.plugin_name == "ctx-test"


async def test_plugin_registry_shutdown_all_calls_shutdown_in_reverse_order() -> None:
    """shutdown_all() calls shutdown() in reverse registration order (LIFO)."""
    shutdown_order: list[str] = []

    class OrderPlugin:
        def __init__(self, name: str) -> None:
            self.name = name
            self.version = "1.0.0"
            self.capability = "test"

        async def initialize(self, context: PluginContext) -> None:
            pass

        async def shutdown(self) -> None:
            shutdown_order.append(self.name)

        async def health(self) -> PluginHealth:
            return PluginHealth(status=PluginStatus.READY)

    registry = PluginRegistry()
    for name in ("alpha", "beta", "gamma"):
        registry.register(OrderPlugin(name))

    await registry.initialize_all()
    await registry.shutdown_all()

    assert shutdown_order == ["gamma", "beta", "alpha"]


async def test_plugin_registry_failed_init_shuts_down_already_initialized() -> None:
    """
    initialize_all() rolls back already-initialized plugins when one fails.

    After rollback, the exception from the failing plugin is re-raised.
    """
    registry = PluginRegistry()
    p1 = DummyPlugin(name="first")
    p2 = DummyPlugin(name="second", fail_init=True)
    registry.register(p1)
    registry.register(p2)

    with pytest.raises(RuntimeError, match="Deliberate init failure"):
        await registry.initialize_all()

    # p1 was initialized before p2 failed — it must have been shut down
    assert p1.initialized is True
    assert p1.shutdown_called is True


async def test_plugin_registry_shutdown_all_never_raises() -> None:
    """shutdown_all() continues even when a plugin's shutdown() raises."""
    registry = PluginRegistry()
    p1 = DummyPlugin(name="p1")
    p2 = DummyPlugin(name="p2", fail_shutdown=True)
    p3 = DummyPlugin(name="p3")
    registry.register(p1)
    registry.register(p2)
    registry.register(p3)
    await registry.initialize_all()
    # Must not raise even though p2.shutdown() raises
    await registry.shutdown_all()
    assert p1.shutdown_called is True
    assert p3.shutdown_called is True


# ---------------------------------------------------------------------------
# health_all
# ---------------------------------------------------------------------------


async def test_plugin_registry_health_all_returns_all_statuses() -> None:
    """health_all() returns a health snapshot for every registered plugin."""
    registry = PluginRegistry()
    p1 = DummyPlugin(name="h1", capability="persistence")
    p2 = DummyPlugin(name="h2", capability="cache")
    registry.register(p1)
    registry.register(p2)
    await registry.initialize_all()

    health = await registry.health_all()

    assert "h1" in health
    assert "h2" in health
    assert isinstance(health["h1"], PluginHealth)
    assert isinstance(health["h2"], PluginHealth)
    assert health["h1"].status == PluginStatus.READY
    assert health["h2"].status == PluginStatus.READY


# ---------------------------------------------------------------------------
# Context manager tests
# ---------------------------------------------------------------------------


async def test_plugin_registry_context_manager_shuts_down_on_exit() -> None:
    """async-with PluginRegistry calls shutdown_all() on normal exit."""
    p = DummyPlugin(name="cm-plugin")
    async with PluginRegistry() as registry:
        registry.register(p)
        await registry.initialize_all()

    assert p.shutdown_called is True


async def test_plugin_registry_context_manager_shuts_down_on_exception() -> None:
    """async-with PluginRegistry calls shutdown_all() even when body raises."""
    p = DummyPlugin(name="exc-plugin")
    with pytest.raises(ValueError, match="boom"):
        async with PluginRegistry() as registry:
            registry.register(p)
            await registry.initialize_all()
            raise ValueError("boom")

    assert p.shutdown_called is True


# ---------------------------------------------------------------------------
# Dataclass immutability tests
# ---------------------------------------------------------------------------


def test_plugin_context_is_frozen_dataclass() -> None:
    """PluginContext is a frozen dataclass — attributes cannot be reassigned."""
    ctx = PluginContext(config={}, plugin_name="test-ctx")
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        ctx.plugin_name = "mutated"  # type: ignore[misc]


def test_plugin_health_is_frozen_dataclass() -> None:
    """PluginHealth is a frozen dataclass — attributes cannot be reassigned."""
    health = PluginHealth(status=PluginStatus.READY, message="ok")
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        health.status = PluginStatus.FAILED  # type: ignore[misc]


# ---------------------------------------------------------------------------
# get_all
# ---------------------------------------------------------------------------


def test_plugin_registry_get_all_returns_all_for_capability() -> None:
    """get_all() returns every plugin registered under the given capability."""
    registry = PluginRegistry()
    p1 = DummyPlugin(name="pg-main", capability="persistence")
    p2 = DummyPlugin(name="pg-replica", capability="persistence")
    p3 = DummyPlugin(name="redis", capability="cache")
    registry.register(p1)
    registry.register(p2)
    registry.register(p3)
    result = registry.get_all("persistence")
    assert result == [p1, p2]
    assert registry.get_all("cache") == [p3]
    assert registry.get_all("queue") == []


# ---------------------------------------------------------------------------
# OpenFramePlugin protocol isinstance check
# ---------------------------------------------------------------------------


def test_dummy_plugin_satisfies_protocol() -> None:
    """DummyPlugin satisfies OpenFramePlugin via structural subtyping."""
    plugin = DummyPlugin()
    assert isinstance(plugin, OpenFramePlugin)
