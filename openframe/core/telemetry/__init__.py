"""
openframe/core/telemetry/
==========================
OTel SDK bootstrap for the OpenFrame ecosystem.

Provides idempotent SDK initialisation, cached tracer and meter accessors,
a platform-agnostic lifecycle event counter, and a matching shutdown that
flushes all buffered spans and metrics before process exit.

Usage::

    from openframe.core.telemetry import (
        setup_telemetry,
        shutdown_telemetry,
        get_tracer,
        get_meter,
        record_lifecycle_event,
    )

    # At application startup (once, in lifespan handler):
    setup_telemetry()

    # Anywhere in the codebase:
    tracer = get_tracer()
    with tracer.start_as_current_span("my.operation"):
        ...

    # Platform lifecycle events (e.g. Modal cold start):
    record_lifecycle_event("cold_start")

    # At application shutdown (lifespan teardown or ApplicationBootstrap.stop()):
    shutdown_telemetry()
"""
from __future__ import annotations

from openframe.core.telemetry.setup import (
    get_meter,
    get_tracer,
    record_error,
    record_lifecycle_event,
    setup_telemetry,
    shutdown_telemetry,
)

__all__ = [
    "setup_telemetry",
    "shutdown_telemetry",
    "get_tracer",
    "get_meter",
    "record_lifecycle_event",
    "record_error",
]
