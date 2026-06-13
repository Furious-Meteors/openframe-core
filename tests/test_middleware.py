"""
tests/test_middleware.py
==========================
Tests for openframe.core.middleware.TelemetryMiddleware.

Covers:
- 200 response is returned correctly
- x-session-id header is injected
- Span status: OK for 2xx, ERROR for 4xx and 5xx
- Lifespan scope passes through without creating a span
- Span attributes: http.method present
- Duration recorded in seconds (value < 1.0 for trivial handler)
- http.server.request.duration unit is "s"
"""
from __future__ import annotations

import pytest
import httpx
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode

from openframe.core.middleware import TelemetryMiddleware
from openframe.core.middleware.types import ASGIScope, Receive, Send


# ---------------------------------------------------------------------------
# ASGI app factories
# ---------------------------------------------------------------------------


def make_http_app(status_code: int = 200, body: bytes = b"ok") -> TelemetryMiddleware:
    """Wrap a trivial ASGI app that returns the given status code."""

    async def inner(scope: ASGIScope, receive: Receive, send: Send) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": status_code,
                "headers": [],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": body,
                "more_body": False,
            }
        )

    return TelemetryMiddleware(inner)


# ---------------------------------------------------------------------------
# Basic response handling
# ---------------------------------------------------------------------------


async def test_middleware_returns_200_response(
    span_exporter: InMemorySpanExporter,
) -> None:
    app = make_http_app(200)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.get("/")
    assert resp.status_code == 200


async def test_middleware_returns_correct_body(
    span_exporter: InMemorySpanExporter,
) -> None:
    app = make_http_app(200, body=b"hello")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.get("/")
    assert resp.content == b"hello"


async def test_middleware_injects_x_session_id(
    span_exporter: InMemorySpanExporter,
) -> None:
    app = make_http_app(200)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.get("/")
    assert "x-session-id" in resp.headers


async def test_middleware_does_not_overwrite_existing_session_id(
    span_exporter: InMemorySpanExporter,
) -> None:
    app = make_http_app(200)
    existing_id = "my-existing-session-abc"
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.get("/", headers={"x-session-id": existing_id})
    assert resp.headers["x-session-id"] == existing_id


# ---------------------------------------------------------------------------
# Span status codes
# ---------------------------------------------------------------------------


async def test_200_response_span_status_ok(
    span_exporter: InMemorySpanExporter,
) -> None:
    app = make_http_app(200)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        await client.get("/")
    spans = span_exporter.get_finished_spans()
    assert len(spans) >= 1
    assert spans[-1].status.status_code == StatusCode.OK


async def test_201_response_span_status_ok(
    span_exporter: InMemorySpanExporter,
) -> None:
    app = make_http_app(201)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        await client.post("/items")
    spans = span_exporter.get_finished_spans()
    assert spans[-1].status.status_code == StatusCode.OK


async def test_404_response_span_status_error(
    span_exporter: InMemorySpanExporter,
) -> None:
    app = make_http_app(404)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        await client.get("/missing")
    spans = span_exporter.get_finished_spans()
    assert spans[-1].status.status_code == StatusCode.ERROR


async def test_500_response_span_status_error(
    span_exporter: InMemorySpanExporter,
) -> None:
    app = make_http_app(500)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        await client.get("/error")
    spans = span_exporter.get_finished_spans()
    assert spans[-1].status.status_code == StatusCode.ERROR


async def test_400_response_span_status_error(
    span_exporter: InMemorySpanExporter,
) -> None:
    app = make_http_app(400)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        await client.get("/bad-request")
    spans = span_exporter.get_finished_spans()
    assert spans[-1].status.status_code == StatusCode.ERROR


# ---------------------------------------------------------------------------
# Span attributes
# ---------------------------------------------------------------------------


async def test_span_has_http_method_attribute(
    span_exporter: InMemorySpanExporter,
) -> None:
    app = make_http_app(200)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        await client.get("/some-path")
    spans = span_exporter.get_finished_spans()
    assert spans[-1].attributes.get("http.method") == "GET"


async def test_span_has_http_method_post(
    span_exporter: InMemorySpanExporter,
) -> None:
    app = make_http_app(201)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        await client.post("/items", json={"name": "test"})
    spans = span_exporter.get_finished_spans()
    assert spans[-1].attributes.get("http.method") == "POST"


async def test_span_has_http_status_code(
    span_exporter: InMemorySpanExporter,
) -> None:
    app = make_http_app(200)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        await client.get("/")
    spans = span_exporter.get_finished_spans()
    assert spans[-1].attributes.get("http.status_code") == 200


# ---------------------------------------------------------------------------
# Non-HTTP scope passthrough
# ---------------------------------------------------------------------------


async def test_lifespan_scope_passes_through_without_span(
    span_exporter: InMemorySpanExporter,
) -> None:
    lifespan_handled = []

    async def inner(scope: ASGIScope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            lifespan_handled.append(True)

    app = TelemetryMiddleware(inner)

    async def noop_receive() -> dict:
        return {"type": "lifespan.startup"}

    async def noop_send(message: dict) -> None:
        pass

    await app({"type": "lifespan"}, noop_receive, noop_send)

    assert lifespan_handled == [True]
    assert len(span_exporter.get_finished_spans()) == 0


# ---------------------------------------------------------------------------
# Metric values — duration in seconds
# ---------------------------------------------------------------------------


async def test_request_duration_is_recorded_in_seconds(
    span_exporter: InMemorySpanExporter,
    metric_reader: InMemoryMetricReader,
) -> None:
    """Duration must be recorded as fractional seconds, not milliseconds."""
    app = make_http_app(200)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        await client.get("/")

    data = metric_reader.get_metrics_data()
    duration_metric = None
    for rm in data.resource_metrics:
        for sm in rm.scope_metrics:
            for m in sm.metrics:
                if m.name == "http.server.request.duration":
                    duration_metric = m
                    break

    assert duration_metric is not None, "http.server.request.duration metric not found"
    assert duration_metric.unit == "s", (
        f"Expected unit 's', got '{duration_metric.unit}'. "
        "Duration must be in seconds per OTel HTTP semconv."
    )
    # For a trivial no-op handler, duration should be well under 1 second.
    # If recorded in ms it would be ~0-50ms, which as a "second" value would
    # still be < 1.0 — so we additionally verify the unit tag is correct.
    data_points = duration_metric.data.data_points
    assert len(data_points) > 0
    total_sum = data_points[0].sum
    assert total_sum < 1.0, (
        f"Duration sum={total_sum}. If this is > 1.0 for a trivial handler, "
        "the middleware may be recording in milliseconds instead of seconds."
    )


async def test_request_count_is_incremented(
    span_exporter: InMemorySpanExporter,
    metric_reader: InMemoryMetricReader,
) -> None:
    app = make_http_app(200)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        await client.get("/")
        await client.get("/")

    data = metric_reader.get_metrics_data()
    assert data is not None, (
        "InMemoryMetricReader returned None — MeterProvider may not have been "
        "set correctly (check reset_telemetry_state fixture)"
    )
    count_metric = None
    for rm in data.resource_metrics:
        for sm in rm.scope_metrics:
            for m in sm.metrics:
                if m.name == "http.server.request.count":
                    count_metric = m
                    break

    assert count_metric is not None, "http.server.request.count metric not found"
    total = sum(dp.value for dp in count_metric.data.data_points)
    assert total == 2
