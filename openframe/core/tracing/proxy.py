"""
openframe/core/tracing/proxy.py
==================================
Generic async telemetry sidecar for the OpenFrame ecosystem.

``TracingProxy`` wraps any object and intercepts every async method call,
creating a child OTel span around it. Neither the adapter nor the service
layer need to know telemetry exists.

Two bugs from the production template are fixed here:

**Bug 1 (original):**
    ``object.__setattr__(self, name, _traced)`` permanently shadows entries
    in ``self.__dict__``. Reconnecting adapters (Postgres pools, Redis clients)
    that replace their own methods after reconnect would silently call the
    stale bound method via the shadowed attribute.

**Bug 2 (v2 fix attempt):**
    Moving to a ``_cache`` dict stopped the shadowing, but the closure still
    captured ``method`` at first-access time — a snapshot. Reconnecting
    adapters still called the stale method object.

**Correct fix (this implementation):**
    The closure re-resolves the method via ``getattr`` on every invocation.
    ``_cache`` stores only the closure allocation — never the resolved method.
    Sync methods are returned directly without caching.

Dependency order: imports ``openframe.core.telemetry`` (lower in DAG). ✓
"""
from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from openframe.core.telemetry.setup import get_tracer

__all__ = ["TracingProxy"]


class TracingProxy:
    """
    Generic async telemetry sidecar.

    Wraps any object and intercepts every async method call, creating a
    child OTel span around it. Neither the adapter nor the service layer
    need to know telemetry exists.

    Span naming::

        {prefix}.{method_name}
        # e.g. "repository.item.get", "queue.kafka.publish"

    Reconnect safety:
        The wrapped method is resolved fresh on every invocation via
        ``getattr`` — never captured as a snapshot. Safe for Postgres
        connection pools, Redis clients, and any adapter that replaces its
        own methods after reconnect.

    Sync methods:
        Pass through unwrapped with no span overhead. Not cached — always
        delegates to the current method on the wrapped object.

    Caching:
        ``_cache`` stores closures keyed by method name to avoid repeated
        closure allocation on hot async paths. It does NOT cache the resolved
        method — that is always fetched live from the wrapped object.

    Usage::

        raw = PostgresRepository(url)
        traced = TracingProxy(raw, prefix="repository.item")
        # traced.get(...)     → span "repository.item.get"
        # traced.create(...)  → span "repository.item.create"
    """

    def __init__(self, wrapped: object, prefix: str) -> None:
        """
        Initialise the proxy.

        Args:
            wrapped: The object whose async methods will be instrumented.
            prefix:  Prefix prepended to every span name, e.g.
                     ``"repository.item"`` or ``"queue.kafka"``.
        """
        object.__setattr__(self, "_wrapped", wrapped)
        object.__setattr__(self, "_prefix", prefix)
        # _cache stores closures by method name.
        # Avoids repeated closure allocation on hot paths.
        # Does NOT cache the resolved method — always live.
        object.__setattr__(self, "_cache", {})

    def __getattr__(self, name: str) -> Any:
        """
        Intercept attribute access.

        Returns a cached traced closure for async methods, or the raw
        attribute for sync methods and non-callable attributes.

        Args:
            name: The attribute name being accessed.

        Returns:
            For async methods: a cached ``_traced`` coroutine closure.
            For everything else: the raw attribute from the wrapped object.
        """
        cache: dict[str, Callable[..., Any]] = object.__getattribute__(
            self, "_cache"
        )
        if name in cache:
            return cache[name]

        wrapped = object.__getattribute__(self, "_wrapped")
        # Probe once to determine sync vs async.
        # Do NOT retain this reference — the closure re-resolves on each call.
        probe = getattr(wrapped, name)

        if not asyncio.iscoroutinefunction(probe):
            # Sync or non-callable: return directly without caching.
            # The caller always gets the current attribute from wrapped.
            return probe

        prefix: str = object.__getattribute__(self, "_prefix")

        async def _traced(*args: Any, **kwargs: Any) -> Any:
            # Re-resolve on every invocation — never a stale snapshot.
            # Safe for adapters that replace their own methods after reconnect.
            current = getattr(
                object.__getattribute__(self, "_wrapped"), name
            )
            with get_tracer().start_as_current_span(f"{prefix}.{name}"):
                return await current(*args, **kwargs)

        cache[name] = _traced
        return _traced
