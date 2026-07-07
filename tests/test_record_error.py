"""
tests/test_record_error.py
============================
Tests for openframe.core.telemetry.record_error — the single seam through
which errors flow into telemetry (ADR-006 error-handling schema).

Covers:
- Structured span attributes (error.code / severity / retryable)
- The exception is recorded as a span event
- correlation_id is stamped back onto the error (enrichment on the way up)
- The openframe.error.count metric is emitted exactly once per error object
  (dedupe across multiple seams)
- record_error never raises, even with no active span/provider
"""
from __future__ import annotations

from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from openframe.core.exceptions import (
    AdapterConnectionError,
    AdapterQueryError,
    OpenFrameError,
)
from openframe.core.telemetry.setup import get_tracer, record_error


def _counter_total(metrics_data: object, name: str) -> float:
    """Sum every data point of the named counter across the metrics data."""
    total = 0.0
    if metrics_data is None:
        return total
    for rm in metrics_data.resource_metrics:  # type: ignore[attr-defined]
        for sm in rm.scope_metrics:
            for metric in sm.metrics:
                if metric.name == name:
                    for point in metric.data.data_points:
                        total += point.value
    return total


# ---------------------------------------------------------------------------
# Span annotation
# ---------------------------------------------------------------------------


def test_record_error_sets_structured_span_attributes(
    span_exporter: InMemorySpanExporter,
) -> None:
    err = AdapterConnectionError("boom", adapter="postgres", operation="connect")
    with get_tracer().start_as_current_span("test.op") as span:
        record_error(err, span=span)

    spans = span_exporter.get_finished_spans()
    assert len(spans) == 1
    attrs = spans[0].attributes
    assert attrs["error.code"] == "adapter.connection"
    assert attrs["error.severity"] == "error"
    assert attrs["error.retryable"] is True


def test_record_error_records_exception_event(
    span_exporter: InMemorySpanExporter,
) -> None:
    err = AdapterQueryError("q failed", adapter="postgres", operation="list")
    with get_tracer().start_as_current_span("test.op") as span:
        record_error(err, span=span)

    spans = span_exporter.get_finished_spans()
    assert any(event.name == "exception" for event in spans[0].events)


def test_record_error_stamps_correlation_id(
    span_exporter: InMemorySpanExporter,
) -> None:
    err = OpenFrameError("x")
    assert err.correlation_id is None
    with get_tracer().start_as_current_span("test.op") as span:
        record_error(err, span=span)
    assert err.correlation_id is not None
    assert len(err.correlation_id) == 32


def test_record_error_does_not_overwrite_existing_correlation_id(
    span_exporter: InMemorySpanExporter,
) -> None:
    err = OpenFrameError("x", correlation_id="preset")
    with get_tracer().start_as_current_span("test.op") as span:
        record_error(err, span=span)
    assert err.correlation_id == "preset"


# ---------------------------------------------------------------------------
# Metric emission + dedupe
# ---------------------------------------------------------------------------


def test_record_error_emits_counter(metric_reader: InMemoryMetricReader) -> None:
    err = AdapterQueryError("q", adapter="pg", operation="list")
    record_error(err)
    total = _counter_total(metric_reader.get_metrics_data(), "openframe.error.count")
    assert total == 1


def test_record_error_counts_each_error_once_across_seams(
    metric_reader: InMemoryMetricReader,
) -> None:
    """A single error passing through multiple seams is counted once."""
    err = AdapterConnectionError("boom", adapter="pg", operation="connect")
    record_error(err)  # e.g. TracingProxy seam
    record_error(err)  # e.g. TelemetryMiddleware seam
    record_error(err)  # e.g. any further boundary
    total = _counter_total(metric_reader.get_metrics_data(), "openframe.error.count")
    assert total == 1


def test_record_error_counts_distinct_errors_separately(
    metric_reader: InMemoryMetricReader,
) -> None:
    record_error(AdapterQueryError("a", adapter="pg", operation="get"))
    record_error(AdapterQueryError("b", adapter="pg", operation="get"))
    total = _counter_total(metric_reader.get_metrics_data(), "openframe.error.count")
    assert total == 2


# ---------------------------------------------------------------------------
# Robustness
# ---------------------------------------------------------------------------


def test_record_error_never_raises_without_active_span() -> None:
    """record_error must not raise even with no active span or provider."""
    record_error(ValueError("plain non-openframe error"))


def test_record_error_handles_non_openframe_error(
    span_exporter: InMemorySpanExporter,
) -> None:
    """A raw exception is still recorded on the span without error.code attrs."""
    with get_tracer().start_as_current_span("test.op") as span:
        record_error(ValueError("raw"), span=span)
    spans = span_exporter.get_finished_spans()
    assert any(event.name == "exception" for event in spans[0].events)
