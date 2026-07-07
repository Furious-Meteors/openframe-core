"""
openframe/core/tracing/propagation.py
=======================================
W3C TraceContext inject/extract helpers for message-broker adapters.

Thin, named wrappers around the OTel propagator API. Every adapter that
needs to carry trace context across a process boundary (Kafka, NATS,
RabbitMQ, SQS, …) imports from here rather than reaching into the OTel SDK
directly, giving a single versioned interface and a mockable seam for tests.

The active propagator is configured by ``setup_telemetry()`` (defaults to
W3C TraceContext + Baggage). Both functions are no-ops until the SDK is
initialised.

Producer (inject) usage::

    from openframe.core.tracing.propagation import inject

    headers: dict[str, str] = {}
    inject(headers)
    await producer.send(topic, value=payload, headers=headers)
    # headers now contains {"traceparent": "00-<trace_id>-<span_id>-01", ...}

Consumer (extract) usage::

    from openframe.core.tracing.propagation import extract

    ctx = extract(message.headers)
    with tracer.start_as_current_span("consume.message", context=ctx):
        await handler(message.value)

Dependency order: imports ``opentelemetry.propagate`` (external OTel API).
No openframe.core.* imports — safe at the leaf of the tracing sub-package.
"""
from __future__ import annotations

from typing import MutableMapping

from opentelemetry import context, propagate

__all__ = ["inject", "extract"]


def inject(carrier: MutableMapping[str, str]) -> None:
    """
    Inject the active trace context into *carrier*.

    Mutates *carrier* in place, adding the W3C ``traceparent`` header (and
    ``tracestate`` / ``baggage`` if present). A no-op when there is no active
    span or the SDK has not been initialised.

    Args:
        carrier: A mutable string-to-string mapping, e.g. a Kafka headers
                 dict or an AMQP message properties map.
    """
    propagate.inject(carrier)


def extract(carrier: MutableMapping[str, str]) -> context.Context:
    """
    Extract a trace context from *carrier*.

    Reads the W3C ``traceparent`` (and ``tracestate`` / ``baggage``) from
    *carrier* and returns an OTel ``Context`` object. Pass this to
    ``tracer.start_as_current_span(..., context=ctx)`` to make the new span a
    child of the upstream trace. Returns an empty context when no valid
    ``traceparent`` is found.

    Args:
        carrier: A string-to-string mapping carrying trace headers, e.g.
                 a decoded Kafka headers dict or an AMQP message headers map.

    Returns:
        An OTel ``Context`` with the extracted span context as the current
        span, or an empty context if extraction fails.
    """
    return propagate.extract(carrier)
