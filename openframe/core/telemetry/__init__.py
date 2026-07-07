"""
openframe/core/telemetry/
==========================
OTel SDK bootstrap for the OpenFrame ecosystem.

Provides idempotent SDK initialisation, cached tracer and meter accessors,
and a platform-agnostic lifecycle event counter.

Usage::

    from openframe.core.telemetry import (
        setup_telemetry,
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
"""
from __future__ import annotations

from openframe.core.telemetry.setup import (
    get_meter,
    get_tracer,
    record_error,
    record_lifecycle_event,
    setup_telemetry,
)

__all__ = [
    "setup_telemetry",
    "get_tracer",
    "get_meter",
    "record_lifecycle_event",
    "record_error",
]
