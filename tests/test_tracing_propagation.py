"""
tests/test_tracing_propagation.py
===================================
Tests for ``openframe.core.tracing.propagation`` — inject / extract helpers.

Covers:
- inject() writes a W3C traceparent header into an empty carrier
- inject() is a no-op (no traceparent) when there is no active span
- extract() returns a context containing the span from a valid traceparent
- extract() returns an empty context for a missing/invalid traceparent
- Round-trip: inject then extract preserves trace_id and span_id
- Submodule is importable directly from openframe.core.tracing
"""
from __future__ import annotations

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from openframe.core.tracing import propagation
from openframe.core.tracing.propagation import extract, inject


# ---------------------------------------------------------------------------
# inject()
# ---------------------------------------------------------------------------


def test_inject_adds_traceparent_inside_active_span(
    span_exporter: InMemorySpanExporter,
) -> None:
    """inject() writes a valid traceparent header when a span is active."""
    tracer = trace.get_tracer("test")
    carrier: dict[str, str] = {}

    with tracer.start_as_current_span("test.span"):
        inject(carrier)

    assert "traceparent" in carrier
    # W3C traceparent format: 00-<32 hex trace_id>-<16 hex span_id>-<flags>
    parts = carrier["traceparent"].split("-")
    assert len(parts) == 4
    assert parts[0] == "00"
    assert len(parts[1]) == 32  # trace_id
    assert len(parts[2]) == 16  # span_id


def test_inject_no_active_span_produces_no_traceparent() -> None:
    """inject() is a no-op when there is no active recording span."""
    carrier: dict[str, str] = {}
    inject(carrier)
    assert "traceparent" not in carrier


def test_inject_mutates_carrier_in_place(span_exporter: InMemorySpanExporter) -> None:
    """inject() mutates the carrier dict passed in, rather than returning a new one."""
    tracer = trace.get_tracer("test")
    carrier: dict[str, str] = {"existing-key": "existing-value"}

    with tracer.start_as_current_span("test.span"):
        inject(carrier)

    assert "existing-key" in carrier
    assert "traceparent" in carrier


# ---------------------------------------------------------------------------
# extract()
# ---------------------------------------------------------------------------


def test_extract_valid_traceparent_returns_populated_context() -> None:
    """extract() returns a context with a valid span when traceparent is present."""
    trace_id = "0af7651916cd43dd8448eb211c80319c"
    span_id = "b7ad6b7169203331"
    carrier = {"traceparent": f"00-{trace_id}-{span_id}-01"}

    ctx = extract(carrier)
    span = trace.get_current_span(ctx)
    span_ctx = span.get_span_context()

    assert span_ctx.is_valid
    assert format(span_ctx.trace_id, "032x") == trace_id
    assert format(span_ctx.span_id, "016x") == span_id


def test_extract_missing_traceparent_returns_empty_context() -> None:
    """extract() returns an empty (invalid) context when carrier has no traceparent."""
    ctx = extract({})
    span = trace.get_current_span(ctx)
    assert not span.get_span_context().is_valid


def test_extract_malformed_traceparent_returns_empty_context() -> None:
    """extract() does not raise on a malformed traceparent — returns empty context."""
    ctx = extract({"traceparent": "not-a-valid-traceparent"})
    span = trace.get_current_span(ctx)
    assert not span.get_span_context().is_valid


# ---------------------------------------------------------------------------
# Round-trip
# ---------------------------------------------------------------------------


def test_inject_extract_round_trip_preserves_trace_and_span_ids() -> None:
    """inject() then extract() restores the exact same trace_id and span_id."""
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("round-trip")

    carrier: dict[str, str] = {}
    with tracer.start_as_current_span("producer.send"):
        inject(carrier)

    finished = exporter.get_finished_spans()
    assert len(finished) == 1
    original_span = finished[0]

    ctx = extract(carrier)
    extracted_span_ctx = trace.get_current_span(ctx).get_span_context()

    assert extracted_span_ctx.is_valid
    assert extracted_span_ctx.trace_id == original_span.context.trace_id
    assert extracted_span_ctx.span_id == original_span.context.span_id


# ---------------------------------------------------------------------------
# Submodule import surface
# ---------------------------------------------------------------------------


def test_propagation_importable_from_tracing_package() -> None:
    """openframe.core.tracing.propagation is re-exported from the package."""
    assert hasattr(propagation, "inject")
    assert hasattr(propagation, "extract")
    assert callable(propagation.inject)
    assert callable(propagation.extract)


def test_propagation_all_exports() -> None:
    """__all__ on propagation contains exactly inject and extract."""
    from openframe.core.tracing import propagation as p

    assert set(p.__all__) == {"inject", "extract"}
