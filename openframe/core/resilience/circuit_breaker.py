"""
openframe/core/resilience/circuit_breaker.py
===============================================
Generic async circuit breaker for the OpenFrame ecosystem.

``CircuitBreakerProxy`` wraps any object and short-circuits its async
methods after a run of consecutive failures, giving a struggling backend
time to recover instead of every caller blocking until ``operation_timeout``
on every single call. Neither the wrapped adapter nor the service layer
need to know the circuit breaker exists.

Mirrors :class:`~openframe.core.tracing.proxy.TracingProxy`'s exact
wrapping mechanism (``__getattr__`` interception, ``object.__setattr__``
for the proxy's own state, fresh ``getattr`` resolution of the wrapped
method on every call — never a stale snapshot) so the two proxies compose
predictably and a reader who understands one understands the other.

State machine (per proxy instance, per wrapped object — not global)::

    CLOSED --[failure_threshold consecutive failures]--> OPEN
    OPEN --[reset_timeout elapsed]--> HALF_OPEN
    HALF_OPEN --[probe call succeeds]--> CLOSED
    HALF_OPEN --[probe call fails]--> OPEN (timer restarts)

Known simplification: multiple concurrent callers arriving right at the
``reset_timeout`` boundary can all be let through as "probes" during the
same half-open window (this implementation does not cap in-flight probes
at exactly one). In practice this only matters under high concurrent call
volume at the exact moment the circuit would reopen or close — it does not
affect the CLOSED/OPEN transitions, which are strictly threshold- and
timeout-gated.

Dependency order: imports ``openframe.core.exceptions`` (lowest layer) only.
No dependency on ``telemetry``/``tracing`` — composes with ``TracingProxy``
by wrapping, not by sharing state.

.. stability: experimental
   New in v3.4.0. API may change based on real usage.
"""
from __future__ import annotations

import asyncio
import inspect
import logging
import time
from collections.abc import Callable
from enum import Enum, auto
from typing import Any

from openframe.core.exceptions import AdapterConnectionError

__all__ = ["CircuitBreakerProxy", "CircuitState"]

__stability__ = "experimental"

_log = logging.getLogger(__name__)


class CircuitState(Enum):
    """Lifecycle state of a single :class:`CircuitBreakerProxy` instance."""

    CLOSED = auto()
    OPEN = auto()
    HALF_OPEN = auto()


class CircuitBreakerProxy:
    """
    Generic async circuit breaker.

    Wraps any object and intercepts every async method call. After
    ``failure_threshold`` consecutive failures, the circuit opens: further
    calls raise :class:`~openframe.core.exceptions.AdapterConnectionError`
    immediately (retryable) without invoking the wrapped method, for
    ``reset_timeout`` seconds. After that window elapses, the next call is
    let through as a probe (half-open); if it succeeds the circuit closes
    and failures reset to zero, if it fails the circuit reopens and the
    timer restarts.

    Reconnect safety:
        Like ``TracingProxy``, the wrapped method is resolved fresh via
        ``getattr`` on every invocation — never captured as a snapshot.

    Sync methods:
        Pass through unwrapped, uncounted — the circuit breaker only
        applies to async methods, matching ``TracingProxy``'s convention.

    Composing with ``TracingProxy``:
        Order matters. ``TracingProxy(CircuitBreakerProxy(repo, ...), ...)``
        traces the circuit breaker's own short-circuit raises as failed
        spans. ``CircuitBreakerProxy(TracingProxy(repo, ...), ...)`` counts
        failures on the traced calls but never creates a span for a
        short-circuited call (the wrapped ``TracingProxy`` is never
        reached while open). Prefer the latter — a call that never reached
        the adapter is not an adapter span.

    .. stability: experimental

    Usage::

        raw = PostgresRepository(settings)
        guarded = CircuitBreakerProxy(raw, failure_threshold=5, reset_timeout=30.0)
        # After 5 consecutive failures, calls raise AdapterConnectionError
        # ("circuit open") immediately for 30s instead of blocking on
        # operation_timeout each time.
    """

    def __init__(
        self,
        wrapped: object,
        *,
        failure_threshold: int = 5,
        reset_timeout: float = 30.0,
        name: str = "circuit-breaker",
    ) -> None:
        """
        Initialise the proxy.

        Args:
            wrapped: The object whose async methods will be guarded.
            failure_threshold: Consecutive failures (per method call,
                across all methods on this proxy) before the circuit opens.
                Must be >= 1.
            reset_timeout: Seconds the circuit stays open before a probe
                call is allowed through (half-open). Must be > 0.
            name: Used as the ``adapter`` field on the
                ``AdapterConnectionError`` raised while open, and in log
                messages — e.g. ``"postgres-primary"``.

        Raises:
            ValueError: ``failure_threshold`` < 1 or ``reset_timeout`` <= 0.
        """
        if failure_threshold < 1:
            raise ValueError(f"failure_threshold must be >= 1, got {failure_threshold!r}")
        if reset_timeout <= 0:
            raise ValueError(f"reset_timeout must be > 0, got {reset_timeout!r}")

        object.__setattr__(self, "_wrapped", wrapped)
        object.__setattr__(self, "_failure_threshold", failure_threshold)
        object.__setattr__(self, "_reset_timeout", reset_timeout)
        object.__setattr__(self, "_name", name)
        object.__setattr__(self, "_cache", {})
        object.__setattr__(self, "_state", CircuitState.CLOSED)
        object.__setattr__(self, "_consecutive_failures", 0)
        object.__setattr__(self, "_opened_at", 0.0)
        # Guards state transitions against concurrent callers racing on
        # the same proxy instance (e.g. two coroutines calling .get()
        # concurrently while the circuit is deciding whether to open).
        object.__setattr__(self, "_lock", asyncio.Lock())

    @property
    def state(self) -> CircuitState:
        """Current circuit state. Read-only — for observability/tests."""
        return object.__getattribute__(self, "_state")

    def __getattr__(self, name: str) -> Any:
        """
        Intercept attribute access.

        Returns a cached guarded closure for async methods, or the raw
        attribute for sync methods and non-callable attributes.
        """
        cache: dict[str, Callable[..., Any]] = object.__getattribute__(self, "_cache")
        if name in cache:
            return cache[name]

        wrapped = object.__getattribute__(self, "_wrapped")
        probe = getattr(wrapped, name)

        if not inspect.iscoroutinefunction(probe):
            return probe

        async def _guarded(*args: Any, **kwargs: Any) -> Any:
            await self._before_call(name)
            try:
                current = getattr(object.__getattribute__(self, "_wrapped"), name)
                result = await current(*args, **kwargs)
            except Exception:
                await self._on_failure(name)
                raise
            else:
                await self._on_success(name)
                return result

        cache[name] = _guarded
        return _guarded

    async def _before_call(self, method_name: str) -> None:
        """
        Called before every guarded invocation.

        Raises ``AdapterConnectionError`` immediately if the circuit is
        open and ``reset_timeout`` has not yet elapsed. If the timeout has
        elapsed, transitions to half-open and lets exactly this one call
        through as a probe.
        """
        lock: asyncio.Lock = object.__getattribute__(self, "_lock")
        async with lock:
            state: CircuitState = object.__getattribute__(self, "_state")
            if state is not CircuitState.OPEN:
                return

            opened_at: float = object.__getattribute__(self, "_opened_at")
            reset_timeout: float = object.__getattribute__(self, "_reset_timeout")
            if time.monotonic() - opened_at < reset_timeout:
                name: str = object.__getattribute__(self, "_name")
                raise AdapterConnectionError(
                    f"circuit open — {name}.{method_name} short-circuited "
                    f"after repeated failures; retry after "
                    f"{reset_timeout - (time.monotonic() - opened_at):.1f}s",
                    adapter=name,
                    operation=method_name,
                )

            # reset_timeout elapsed — allow exactly this call through as a probe.
            object.__setattr__(self, "_state", CircuitState.HALF_OPEN)
            _log.info("CircuitBreakerProxy %r half-open — probing %r", object.__getattribute__(self, "_name"), method_name)

    async def _on_success(self, method_name: str) -> None:
        """Reset failure count and close the circuit on any success."""
        lock: asyncio.Lock = object.__getattribute__(self, "_lock")
        async with lock:
            object.__setattr__(self, "_consecutive_failures", 0)
            if object.__getattribute__(self, "_state") is not CircuitState.CLOSED:
                object.__setattr__(self, "_state", CircuitState.CLOSED)
                _log.info(
                    "CircuitBreakerProxy %r closed — %r succeeded",
                    object.__getattribute__(self, "_name"),
                    method_name,
                )

    async def _on_failure(self, method_name: str) -> None:
        """
        Count the failure. Opens the circuit if the threshold is reached
        (from closed) or immediately re-opens it (from half-open, where a
        single probe failure is sufficient — the backend is still down).
        """
        lock: asyncio.Lock = object.__getattribute__(self, "_lock")
        async with lock:
            state: CircuitState = object.__getattribute__(self, "_state")
            name: str = object.__getattribute__(self, "_name")

            if state is CircuitState.HALF_OPEN:
                object.__setattr__(self, "_state", CircuitState.OPEN)
                object.__setattr__(self, "_opened_at", time.monotonic())
                _log.warning(
                    "CircuitBreakerProxy %r re-opened — probe %r failed", name, method_name
                )
                return

            failures = object.__getattribute__(self, "_consecutive_failures") + 1
            object.__setattr__(self, "_consecutive_failures", failures)
            threshold: int = object.__getattribute__(self, "_failure_threshold")
            if failures >= threshold:
                object.__setattr__(self, "_state", CircuitState.OPEN)
                object.__setattr__(self, "_opened_at", time.monotonic())
                _log.warning(
                    "CircuitBreakerProxy %r opened — %d consecutive failures (last: %r)",
                    name, failures, method_name,
                )
