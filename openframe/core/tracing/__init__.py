"""
openframe/core/tracing/
========================
Async telemetry instrumentation and trace-context propagation for the
OpenFrame ecosystem.

Modules
-------
``TracingProxy``
    Zero-code async telemetry sidecar. Wraps any adapter object and adds
    automatic OTel span instrumentation to every async method, without
    requiring the adapter or service layer to know telemetry exists.

``propagation``
    W3C TraceContext inject/extract helpers for message-broker adapters.
    Use ``inject(headers)`` on the producer side and ``extract(headers)``
    on the consumer side to carry trace context across process boundaries.

Usage::

    from openframe.core.tracing import TracingProxy
    from openframe.core.tracing.propagation import inject, extract

    # Wrap an adapter with auto-instrumentation:
    raw_repo = PostgresRepository(settings)
    traced_repo = TracingProxy(raw_repo, prefix="repository.item")
    # Spans named "repository.item.get", "repository.item.create", etc.

    # Propagate trace context across a message broker:
    headers: dict[str, str] = {}
    inject(headers)
    await producer.send(topic, value=payload, headers=headers)

    ctx = extract(message.headers)
    with tracer.start_as_current_span("consume.message", context=ctx):
        await handler(message.value)
"""
from __future__ import annotations

from openframe.core.tracing import propagation
from openframe.core.tracing.proxy import TracingProxy

__all__ = ["TracingProxy", "propagation"]
