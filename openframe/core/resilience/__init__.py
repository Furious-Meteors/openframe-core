"""
openframe/core/resilience/
============================
Resilience patterns for the OpenFrame ecosystem.

Modules
-------
``CircuitBreakerProxy``
    Zero-code async circuit breaker. Wraps any object and short-circuits
    its async methods after a run of consecutive failures, without
    requiring the adapter or service layer to know it exists. Mirrors
    ``openframe.core.tracing.TracingProxy``'s wrapping mechanism, so the
    two proxies compose predictably.

Usage::

    from openframe.core.resilience import CircuitBreakerProxy

    raw_repo = PostgresRepository(settings)
    guarded_repo = CircuitBreakerProxy(raw_repo, failure_threshold=5, reset_timeout=30.0)
    # After 5 consecutive failures, calls raise AdapterConnectionError
    # ("circuit open") immediately instead of blocking on operation_timeout.

Composing with ``TracingProxy`` — prefer wrapping the traced object, not
the other way around, so a short-circuited call never produces a
misleading adapter span for a call that never reached the adapter::

    from openframe.core.tracing import TracingProxy

    traced = TracingProxy(raw_repo, prefix="repository.item")
    guarded = CircuitBreakerProxy(traced, failure_threshold=5, reset_timeout=30.0)

.. stability: experimental
   New in v3.4.0. Experimental — API may change based on real usage,
   consistent with how ``ApplicationBootstrap``/``PluginRegistry`` started
   experimental and graduated once proven (see their own module docstrings).
"""
from __future__ import annotations

from openframe.core.resilience.circuit_breaker import CircuitBreakerProxy, CircuitState

__all__ = ["CircuitBreakerProxy", "CircuitState"]

__stability__ = "experimental"
