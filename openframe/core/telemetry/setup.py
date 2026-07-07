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

Sidecar deployment (default)
-----------------------------
``setup_telemetry()`` assumes a collector is colocated with this process
(e.g. via Docker ``network_mode: service:<this-service>`` or a Kubernetes
sidecar container) and defaults ``OTEL_EXPORTER_OTLP_ENDPOINT`` to
``http://localhost:4318`` when unset. Set ``OPENFRAME_TELEMETRY_DISABLED=1``
to opt out entirely (no-op providers, nothing exported).

Resilience to collector failure
---------------------------------
``BatchSpanProcessor`` is configured with explicit, bounded
``max_queue_size``/``max_export_batch_size`` (overridable via
``OTEL_BSP_MAX_QUEUE_SIZE`` / ``OTEL_BSP_MAX_EXPORT_BATCH_SIZE``). If the
sidecar is unreachable, this process drops spans once the queue fills and
keeps serving traffic — it never blocks and never grows memory without
bound. Durability against collector restarts (disk-backed queue, retry to
the real backend) is the collector's own responsibility, not this
process's — see the collector's ``sending_queue`` and ``file_storage``
extension.

Environment
-----------
``OPENFRAME_ENV`` is the platform-agnostic deployment environment tag
(values: ``dev``, ``feat``, ``prod``). Modal users should map ``MODAL_ENV``
to ``OPENFRAME_ENV`` in their ``configure_env_vars()`` helper::

    @stub.function(secrets=[...])
    def configure_env_vars():
        os.environ["OPENFRAME_ENV"] = os.environ.get("MODAL_ENV", "dev")

Env vars read:
    OTEL_EXPORTER_OTLP_ENDPOINT     — OTLP base URL. Defaults to
                                       http://localhost:4318 (sidecar
                                       assumption) unless
                                       OPENFRAME_TELEMETRY_DISABLED=1.
    OPENFRAME_TELEMETRY_DISABLED    — set to disable telemetry entirely,
                                       reverting to no-op providers.
    OTEL_EXPORTER_OTLP_HEADERS      — auth headers (handled by OTel SDK).
    OTEL_SERVICE_NAME               — service name tag (default: "openframe").
    OTEL_SERVICE_VERSION            — service version tag (default: "1.0.0").
    OTEL_METRIC_EXPORT_INTERVAL_MS  — metric export interval ms (default: 15000).
    OTEL_BSP_MAX_QUEUE_SIZE         — BatchSpanProcessor queue ceiling (default: 2048).
    OTEL_BSP_MAX_EXPORT_BATCH_SIZE  — BatchSpanProcessor batch size (default: 512).
    OPENFRAME_ENV                   — environment tag: dev / feat / prod.

Middleware note:
    ``TelemetryMiddleware`` calls ``get_tracer()`` and ``get_meter()`` directly.
    It does NOT call ``setup_telemetry()``. Call ``setup_telemetry()`` once at
    application startup (e.g. in a ``lifespan`` handler).

Dependency order: this module imports opentelemetry-* (external) and, for
``record_error``, ``openframe.core.exceptions`` — which is the lowest layer
in the DAG, so importing it here does not invert the dependency order. The
error object never imports telemetry; telemetry reads the error's plain data.
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
from opentelemetry.trace import Status, StatusCode

from openframe.core.exceptions import OpenFrameError

__all__ = [
    "setup_telemetry",
    "shutdown_telemetry",
    "get_tracer",
    "get_meter",
    "record_lifecycle_event",
    "record_error",
]

_INITIALISED: bool = False
_tracer_provider: TracerProvider | None = None
_meter_provider: MeterProvider | None = None
_logger = logging.getLogger(__name__)

# Attribute stamped on an error the first time record_error counts it, so a
# single error bubbling through multiple seams (TracingProxy, middleware) is
# counted in the openframe.error.count metric exactly once. Spans are still
# annotated at every seam — nested spans each showing the error is desirable.
_ERROR_RECORDED_FLAG = "_openframe_error_recorded"


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

    # Sidecar-aware default: assume a colocated collector at the standard
    # OTLP HTTP port unless explicitly disabled. This makes "deploy a
    # sidecar collector" the assumed shape rather than requiring every
    # service to know and set the endpoint itself.
    #
    # Set OPENFRAME_TELEMETRY_DISABLED=1 to opt out entirely (no-op mode,
    # same as the old behaviour when no endpoint was configured).
    disabled = os.environ.get("OPENFRAME_TELEMETRY_DISABLED", "").lower() in (
        "1", "true", "yes",
    )
    default_endpoint = "" if disabled else "http://localhost:4318"
    endpoint = os.environ.get(
        "OTEL_EXPORTER_OTLP_ENDPOINT", default_endpoint
    ).rstrip("/")
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
                OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces"),
                # Explicit, bounded ceilings rather than SDK defaults.
                # If the collector is unreachable (sidecar restarting,
                # crashed, not yet started), this queue fills, drops the
                # OLDEST spans first, and the app keeps serving traffic at
                # full speed. Bounded-loss, never unbounded memory growth
                # inside the app process — durability against collector
                # failure belongs to the collector's own sending_queue /
                # file_storage, not to this process.
                max_queue_size=int(
                    os.environ.get("OTEL_BSP_MAX_QUEUE_SIZE", "2048")
                ),
                max_export_batch_size=int(
                    os.environ.get("OTEL_BSP_MAX_EXPORT_BATCH_SIZE", "512")
                ),
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

    global _tracer_provider, _meter_provider
    trace.set_tracer_provider(tracer_provider)
    metrics.set_meter_provider(meter_provider)
    _tracer_provider = tracer_provider
    _meter_provider = meter_provider

    LoggingInstrumentor().instrument(set_logging_format=True)

    _INITIALISED = True


def shutdown_telemetry() -> None:
    """
    Flush and shut down the OTel SDK.

    Forces the ``BatchSpanProcessor`` to export all buffered spans and the
    ``PeriodicExportingMetricReader`` to flush its last data point before the
    process exits. Must be called at application shutdown — in the ``lifespan``
    handler's teardown path, or via ``ApplicationBootstrap.stop()``.

    Idempotent — safe to call even if ``setup_telemetry()`` was never called,
    and safe to call multiple times. Resets the ``_INITIALISED`` guard and
    clears the ``lru_cache`` entries so ``setup_telemetry()`` can run again
    (useful in tests).

    This function never raises — a shutdown error must not mask the original
    exception propagating through a ``finally`` block.
    """
    global _INITIALISED, _tracer_provider, _meter_provider

    if _tracer_provider is not None:
        try:
            _tracer_provider.shutdown()
        except Exception:  # noqa: BLE001
            _logger.debug("shutdown_telemetry: TracerProvider shutdown failed", exc_info=True)
        _tracer_provider = None

    if _meter_provider is not None:
        try:
            _meter_provider.shutdown()
        except Exception:  # noqa: BLE001
            _logger.debug("shutdown_telemetry: MeterProvider shutdown failed", exc_info=True)
        _meter_provider = None

    get_tracer.cache_clear()
    get_meter.cache_clear()
    _INITIALISED = False


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


def record_error(err: Exception, *, span: trace.Span | None = None) -> None:
    """
    Record an error onto the current span and the error metric counter.

    This is the single seam through which errors flow into telemetry. It is
    called at each architectural boundary (``TracingProxy``,
    ``TelemetryMiddleware``, ``PluginRegistry`` lifecycle) so that any error —
    whether it reaches an HTTP request, an adapter call, or startup — is
    observable.

    On the span it:
    - records the exception (stack trace) and sets ERROR status,
    - for an :class:`~openframe.core.exceptions.OpenFrameError`, sets the
      ``error.code`` / ``error.severity`` / ``error.retryable`` attributes,
    - stamps the active trace id back onto ``err.correlation_id`` (enrichment
      on the way up — the error never fetches it itself).

    On metrics it increments ``openframe.error.count`` (labelled only by the
    low-cardinality ``error.code``) exactly once per error object, even if the
    error passes through several seams.

    This function never raises — a telemetry failure must not mask the
    original error being propagated.

    Args:
        err:  The exception being propagated.
        span: The span to annotate. Defaults to the current active span.
    """
    target_span = span if span is not None else trace.get_current_span()

    try:
        target_span.record_exception(err)
        target_span.set_status(Status(StatusCode.ERROR, str(err)))

        if isinstance(err, OpenFrameError):
            target_span.set_attribute("error.code", str(err.code))
            target_span.set_attribute("error.severity", str(err.severity))
            target_span.set_attribute("error.retryable", bool(err.retryable))

            ctx = target_span.get_span_context()
            if err.correlation_id is None and ctx is not None and ctx.is_valid:
                err.correlation_id = format(ctx.trace_id, "032x")
    except Exception:  # noqa: BLE001 — telemetry must never mask the real error
        _logger.debug("record_error: span annotation failed", exc_info=True)

    if getattr(err, _ERROR_RECORDED_FLAG, False):
        return

    try:
        code = getattr(err, "code", "unknown")
        meter = get_meter()
        counter = meter.create_counter(
            name="openframe.error.count",
            description="Count of OpenFrame errors recorded to telemetry.",
            unit="1",
        )
        counter.add(1, {"error.code": str(code)})
        setattr(err, _ERROR_RECORDED_FLAG, True)
    except Exception:  # noqa: BLE001 — telemetry must never mask the real error
        _logger.debug("record_error: metric emission failed", exc_info=True)