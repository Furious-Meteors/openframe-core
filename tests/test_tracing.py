"""
tests/test_tracing.py
=======================
Tests for openframe.core.tracing — TracingProxy.

Covers:
- Async method calls create OTel spans with correct names
- Return values pass through unchanged
- Sync methods pass through unwrapped (no span created)
- Method closures are cached in _cache (avoids re-allocation)
- Second access to the same async method returns the same closure object
- Reconnect safety: method resolved fresh on every call
"""
from __future__ import annotations

import pytest
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from openframe.core.tracing import TracingProxy


# ---------------------------------------------------------------------------
# Helper adapter classes
# ---------------------------------------------------------------------------


class AsyncAdapter:
    """Simple adapter with one async and one sync method."""

    def __init__(self, return_value: object = "result") -> None:
        self._return_value = return_value
        self.calls: list[str] = []

    async def do_work(self) -> object:
        """Async method — should be wrapped with a span."""
        self.calls.append("do_work")
        return self._return_value

    def sync_method(self) -> str:
        """Sync method — must pass through without a span."""
        return "sync_result"


# ---------------------------------------------------------------------------
# Span creation
# ---------------------------------------------------------------------------


async def test_async_method_creates_span(
    span_exporter: InMemorySpanExporter,
) -> None:
    wrapped = AsyncAdapter()
    proxy = TracingProxy(wrapped, "test_prefix")
    await proxy.do_work()
    spans = span_exporter.get_finished_spans()
    assert len(spans) == 1


async def test_span_name_is_prefix_dot_method(
    span_exporter: InMemorySpanExporter,
) -> None:
    wrapped = AsyncAdapter()
    proxy = TracingProxy(wrapped, "test_prefix")
    await proxy.do_work()
    spans = span_exporter.get_finished_spans()
    assert spans[0].name == "test_prefix.do_work"


async def test_custom_prefix_in_span_name(
    span_exporter: InMemorySpanExporter,
) -> None:
    wrapped = AsyncAdapter()
    proxy = TracingProxy(wrapped, "repository.item")
    await proxy.do_work()
    spans = span_exporter.get_finished_spans()
    assert spans[0].name == "repository.item.do_work"


async def test_async_method_return_value_passes_through(
    span_exporter: InMemorySpanExporter,
) -> None:
    wrapped = AsyncAdapter(return_value="hello world")
    proxy = TracingProxy(wrapped, "test_prefix")
    result = await proxy.do_work()
    assert result == "hello world"


# ---------------------------------------------------------------------------
# Sync passthrough
# ---------------------------------------------------------------------------


async def test_sync_method_creates_no_span(
    span_exporter: InMemorySpanExporter,
) -> None:
    wrapped = AsyncAdapter()
    proxy = TracingProxy(wrapped, "test_prefix")
    result = proxy.sync_method()
    assert result == "sync_result"
    assert len(span_exporter.get_finished_spans()) == 0


async def test_sync_method_delegates_to_wrapped(
    span_exporter: InMemorySpanExporter,
) -> None:
    wrapped = AsyncAdapter()
    proxy = TracingProxy(wrapped, "test_prefix")
    assert proxy.sync_method() == "sync_result"


# ---------------------------------------------------------------------------
# Closure caching
# ---------------------------------------------------------------------------


async def test_async_method_closure_is_cached_after_first_access(
    span_exporter: InMemorySpanExporter,
) -> None:
    wrapped = AsyncAdapter()
    proxy = TracingProxy(wrapped, "test_prefix")
    # First access — populates _cache
    _ = proxy.do_work
    cache = object.__getattribute__(proxy, "_cache")
    assert "do_work" in cache


async def test_async_method_same_closure_on_repeated_access(
    span_exporter: InMemorySpanExporter,
) -> None:
    """Two accesses to the same async method return the identical closure."""
    wrapped = AsyncAdapter()
    proxy = TracingProxy(wrapped, "test_prefix")
    first = proxy.do_work
    second = proxy.do_work
    assert first is second


async def test_multiple_calls_accumulate_spans(
    span_exporter: InMemorySpanExporter,
) -> None:
    wrapped = AsyncAdapter()
    proxy = TracingProxy(wrapped, "test_prefix")
    await proxy.do_work()
    await proxy.do_work()
    await proxy.do_work()
    assert len(span_exporter.get_finished_spans()) == 3


# ---------------------------------------------------------------------------
# Reconnect safety — fresh method resolution
# ---------------------------------------------------------------------------


async def test_proxy_resolves_method_fresh_after_replacement(
    span_exporter: InMemorySpanExporter,
) -> None:
    """
    After the wrapped object's method is replaced (simulating reconnect),
    the proxy must call the new method, not the stale snapshot captured at
    first access.

    This validates the v3 fix: the closure does getattr(wrapped, name) on
    every invocation rather than closing over the original method object.
    """
    wrapped = AsyncAdapter(return_value="original")
    proxy = TracingProxy(wrapped, "test_prefix")

    result1 = await proxy.do_work()
    assert result1 == "original"

    # Simulate adapter replacing its method after reconnect
    async def updated_do_work() -> str:
        return "updated_after_reconnect"

    # Instance-level attribute shadows the class method —
    # getattr(wrapped, "do_work") will now return this function.
    wrapped.do_work = updated_do_work  # type: ignore[method-assign]

    result2 = await proxy.do_work()
    assert result2 == "updated_after_reconnect"


async def test_proxy_calls_underlying_method_correctly(
    span_exporter: InMemorySpanExporter,
) -> None:
    """Verify the underlying adapter method is actually called."""
    wrapped = AsyncAdapter()
    proxy = TracingProxy(wrapped, "test_prefix")
    await proxy.do_work()
    assert "do_work" in wrapped.calls
