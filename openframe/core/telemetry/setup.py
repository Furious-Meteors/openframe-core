"""
openframe/core/telemetry/setup.py
====================================
OTel SDK bootstrap for the OpenFrame ecosystem.

Initialises the OpenTelemetry SDK once — idempotent via ``_INITIALISED`` guard.
Provides cached tracer and meter accessors used by ``TracingProxy`` and
``TelemetryMiddleware``.

Authentication
--------------
OTLP authentication is handled natively by the OTel SDK via the
``OTEL_EXPORTER_OTLP_HEADERS`` environment variable. Set it in the format::

    OTEL_EXPORTER_OTLP_HEADERS="Authorization=Basic <base64_token>"

For Grafana Cloud::

    OTEL_EXPORTER_OTLP_HEADERS="Authorization=Basic $(echo -n '<user>:<token>' | base64)"

No vendor-specific header construction lives in this module.

Environment
-----------
``OPENFRAME_ENV`` is the platform-agnostic deployment environment tag
(values: ``dev``, ``feat``, ``prod``). Modal users should map ``MODAL_ENV``
to ``OPENFRAME_ENV`` in their ``configure_env_vars()`` helper::

    @stub.function(secrets=[...])
    def configure_env_vars():
        os.environ["OPENFRAME_ENV"] = os.environ.get("MODAL_ENV", "dev")

Env vars read:
    OTEL_EXPORTER_OTLP_ENDPOINT    — OTLP base URL (required for live export).
                                     When absent, no-op providers are used and
                                     no data is exported.
    OTEL_EXPORTER_OTLP_HEADERS     — auth headers (handled by OTel SDK).
    OTEL_SERVICE_NAME              — service name tag (default: "openframe").
    OTEL_SERVICE_VERSION           — service version tag (default: "1.0.0").
    OTEL_METRIC_EXPORT_INTERVAL_MS — metric export interval ms (default: 15000).
    OPENFRAME_ENV                  — environment tag: dev / feat / prod.

Middleware note:
    ``TelemetryMiddleware`` calls ``get_tracer()`` and ``get_meter()`` directly.
    It does NOT call ``setup_telemetry()``. Call ``setup_telemetry()`` once at
    application startup (e.g. in a ``lifespan`` handler).

Dependency order: this module imports opentelemetry-* (external) only.
No openframe.core imports.
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

__all__ = [
    "setup_telemetry",
    "get_tracer",
    "get_meter",
    "record_lifecycle_event",
]

_INITIALISED: bool = False
_logger = logging.getLogger(__name__)


def setup_telemetry() -> None:
    """
    Initialise the OTel SDK. Idempotent — safe to call multiple times.

    When ``OTEL_EXPORTER_OTLP_ENDPOINT`` is set, configures OTLP exporters
    for both traces and metrics. When absent, installs no-op providers so
    calls to ``get_tracer()`` and ``get_meter()`` succeed but produce no
    exported data.

    Applies ``LoggingInstrumentor`` so every ``logging.Logger`` call
    automatically includes the active trace_id and span_id in the log record.

    Must be called once at application startup (e.g. in a ``lifespan``
    handler). Do NOT call this inside ``TelemetryMiddleware`` — doing so
    would overwrite any ``TracerProvider`` already set by the test harness.

    Raises:
        Nothing — all errors are logged and setup degrades gracefully.
    """
    global _INITIALISED
    if _INITIALISED:
        return

    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").rstrip("/")
    service_name = os.environ.get("OTEL_SERVICE_NAME", "openframe")
    service_version = os.environ.get("OTEL_SERVICE_VERSION", "1.0.0")
    environment = os.environ.get("OPENFRAME_ENV", "dev")
    metric_interval_ms = int(
        os.environ.get("OTEL_METRIC_EXPORT_INTERVAL_MS", "15000")
    )

    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": service_version,
            "deployment.environment": environment,
        }
    )

    if endpoint:
        tracer_provider = TracerProvider(resource=resource)
        tracer_provider.add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces")
            )
        )

        metric_reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=f"{endpoint}/v1/metrics"),
            export_interval_millis=metric_interval_ms,
        )
        meter_provider = MeterProvider(
            resource=resource,
            metric_readers=[metric_reader],
        )
        _logger.info(
            "OpenTelemetry SDK initialised — exporting to %s (service=%s env=%s)",
            endpoint,
            service_name,
            environment,
        )
    else:
        tracer_provider = TracerProvider(resource=resource)
        meter_provider = MeterProvider(resource=resource)
        _logger.info(
            "OpenTelemetry SDK initialised — no-op mode "
            "(set OTEL_EXPORTER_OTLP_ENDPOINT to enable export)",
        )

    trace.set_tracer_provider(tracer_provider)
    metrics.set_meter_provider(meter_provider)

    LoggingInstrumentor().instrument(set_logging_format=True)

    _INITIALISED = True


@lru_cache(maxsize=32)
def get_tracer(name: str | None = None) -> trace.Tracer:
    """
    Return a cached ``Tracer`` for the given name.

    Uses the globally-set ``TracerProvider`` (configured by ``setup_telemetry()``
    or by a test fixture via ``trace.set_tracer_provider()``).

    The result is cached per ``name`` via ``lru_cache``. Call
    ``get_tracer.cache_clear()`` in tests to reset between test runs.

    Args:
        name: Instrumentation scope name. Defaults to ``OTEL_SERVICE_NAME``
              or ``"openframe"`` if not set.

    Returns:
        A ``Tracer`` bound to the current global ``TracerProvider``.
    """
    scope_name = name or os.environ.get("OTEL_SERVICE_NAME", "openframe")
    return trace.get_tracer(scope_name)


@lru_cache(maxsize=32)
def get_meter(name: str | None = None) -> metrics.Meter:
    """
    Return a cached ``Meter`` for the given name.

    Uses the globally-set ``MeterProvider`` (configured by ``setup_telemetry()``
    or by a test fixture via ``metrics.set_meter_provider()``).

    The result is cached per ``name`` via ``lru_cache``. Call
    ``get_meter.cache_clear()`` in tests to reset between test runs.

    Args:
        name: Instrumentation scope name. Defaults to ``OTEL_SERVICE_NAME``
              or ``"openframe"`` if not set.

    Returns:
        A ``Meter`` bound to the current global ``MeterProvider``.
    """
    scope_name = name or os.environ.get("OTEL_SERVICE_NAME", "openframe")
    return metrics.get_meter(scope_name)


def record_lifecycle_event(
    event_name: str,
    attributes: dict[str, str] | None = None,
) -> None:
    """
    Increment a named lifecycle event counter.

    Platform-agnostic replacement for ``record_cold_start()``. Templates
    call this at the points where the platform fires lifecycle events::

        # In a Modal function's cold-start path:
        record_lifecycle_event("cold_start")

        # With extra context:
        record_lifecycle_event("worker_restart", {"reason": "oom"})

    The metric name is ``lifecycle.<event_name>``, unit ``1``.

    The OTel SDK deduplicates counter instruments by name, so repeated
    calls with the same ``event_name`` are safe and efficient.

    Args:
        event_name:  Name of the lifecycle event (e.g. ``"cold_start"``).
        attributes:  Optional key-value labels attached to this data point.
    """
    meter = get_meter()
    counter = meter.create_counter(
        name=f"lifecycle.{event_name}",
        description=f"Count of '{event_name}' lifecycle events",
        unit="1",
    )
    counter.add(1, attributes or {})
