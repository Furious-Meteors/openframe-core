"""
openframe/core/middleware/telemetry.py
=========================================
Pure ASGI telemetry middleware for the OpenFrame ecosystem.

Records an OTel span and HTTP metrics for every inbound HTTP request.
Compatible with any ASGI framework: FastAPI, Starlette, Litestar, or bare ASGI.

CRITICAL — setup_telemetry():
    This middleware does NOT call ``setup_telemetry()``. Call ``setup_telemetry()``
    once at application startup (e.g. in a ``lifespan`` handler). This middleware
    calls ``get_tracer()`` and ``get_meter()`` directly against whatever
    ``TracerProvider`` and ``MeterProvider`` are currently set.

    An implementer who adds ``setup_telemetry()`` inside the middleware will
    silently overwrite any ``TracerProvider`` already configured (including the
    test fixture's ``InMemorySpanExporter``), breaking all span assertions in CI.

Route template extraction:
    Raw ASGI: ``scope["path"]`` gives the raw path (``/items/abc-123``).
              Metric cardinality from path params is a known trade-off when
              no router reference is available.

    Starlette/FastAPI: after routing, Starlette sets ``scope["route"]`` to the
              matched ``Route`` object. Extract the template with::

                  route_obj = scope.get("route")
                  route = route_obj.path if route_obj is not None else scope.get("path", "/")

Instruments (lazy — created on first HTTP request):
    ``http.server.request.count``     counter         unit="1"
    ``http.server.request.duration``  histogram       unit="s"  (OTel semconv — seconds)
    ``http.server.active_requests``   updowncounter   unit="1"
    ``http.server.error.count``       counter         unit="1"  (4xx + 5xx only)
    ``http.server.response.size``     histogram       unit="By"

Span attributes set:
    ``http.method``, ``http.target``, ``http.route``, ``http.scheme``,
    ``http.status_code``, ``http.user_agent``, ``net.host.name``,
    ``http.client_ip``, ``app.session_id``

Dependency order: imports from ``openframe.core.telemetry`` (lower in DAG). ✓
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from opentelemetry.trace import StatusCode

from openframe.core.middleware.types import ASGIApp, ASGIMessage, ASGIScope, Receive, Send
from openframe.core.telemetry.setup import get_meter, get_tracer

__all__ = ["TelemetryMiddleware"]

_logger = logging.getLogger(__name__)


class TelemetryMiddleware:
    """
    Pure ASGI telemetry middleware.

    Records an OTel span and HTTP metrics for every inbound HTTP request.
    Compatible with FastAPI, Starlette, Litestar, or bare ASGI.

    This middleware does NOT call ``setup_telemetry()``. Call it once at
    application startup. This middleware uses ``get_tracer()`` and
    ``get_meter()`` directly against whatever providers are currently set.

    Route template:
        Starlette/FastAPI users: ``scope["route"].path`` if available,
        falling back to ``scope["path"]``.

    ``x-session-id`` header:
        Injected on every response that doesn't already carry one.
        Generated with ``uuid.uuid4()`` and included in the span and log.

    Span status:
        ``StatusCode.OK`` for status < 400.
        ``StatusCode.ERROR`` for status >= 400 or unhandled exception.

    Metrics unit:
        ``http.server.request.duration`` is recorded in fractional seconds
        (unit ``"s"``) per OTel HTTP semantic conventions. Any observability
        backend (Grafana, Honeycomb, Datadog) that ingests this metric name
        assumes seconds.

    Usage::

        app = TelemetryMiddleware(app)
    """

    def __init__(self, app: ASGIApp) -> None:
        """
        Wrap an ASGI application with telemetry instrumentation.

        Args:
            app: The inner ASGI application to wrap.
        """
        self._app = app
        # Lazy instrument map — populated on first HTTP request.
        # Key: instrument logical name. Value: OTel instrument instance.
        self._instruments: dict[str, Any] = {}

    def _ensure_instruments(self) -> None:
        """
        Lazily initialise metric instruments on the first HTTP request.

        Defers meter creation until the first request so that a
        ``MeterProvider`` configured after middleware construction (e.g. by
        a ``lifespan`` handler that calls ``setup_telemetry()``) is used
        rather than the provider set at import time.
        """
        if self._instruments:
            return
        meter = get_meter()
        self._instruments = {
            "request_count": meter.create_counter(
                name="http.server.request.count",
                description="Total number of HTTP server requests received.",
                unit="1",
            ),
            "request_duration": meter.create_histogram(
                name="http.server.request.duration",
                description=(
                    "Duration of HTTP server requests in seconds. "
                    "Unit 's' per OTel HTTP semantic conventions."
                ),
                unit="s",
            ),
            "active_requests": meter.create_up_down_counter(
                name="http.server.active_requests",
                description="Number of HTTP requests currently being processed.",
                unit="1",
            ),
            "error_count": meter.create_counter(
                name="http.server.error.count",
                description="Number of HTTP error responses (4xx and 5xx).",
                unit="1",
            ),
            "response_size": meter.create_histogram(
                name="http.server.response.size",
                description="Size of HTTP response bodies in bytes.",
                unit="By",
            ),
        }

    async def __call__(
        self,
        scope: ASGIScope,
        receive: Receive,
        send: Send,
    ) -> None:
        """
        ASGI entry point.

        Only HTTP scopes are instrumented. Lifespan and WebSocket scopes
        are passed directly to the inner app without creating any span or
        incrementing any metric.

        Args:
            scope:   ASGI scope dict (contains "type", "method", "path", etc.).
            receive: Callable that returns the next ASGI message from the client.
            send:    Callable that sends an ASGI message to the client.
        """
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        self._ensure_instruments()
        await self._handle_http(scope, receive, send)

    async def _handle_http(
        self,
        scope: ASGIScope,
        receive: Receive,
        send: Send,
    ) -> None:
        """
        Instrument a single HTTP request end-to-end.

        Creates an OTel span, records all metric instruments, injects
        ``x-session-id``, and emits a structured log line.

        Args:
            scope:   ASGI scope dict for this HTTP request.
            receive: ASGI receive callable.
            send:    ASGI send callable.
        """
        method: str = scope.get("method", "GET")
        path: str = scope.get("path", "/")
        scheme: str = scope.get("scheme", "http")

        server = scope.get("server")
        host: str = server[0] if isinstance(server, (list, tuple)) and server else "localhost"

        # Prefer route template from Starlette/FastAPI router over raw path.
        route_obj = scope.get("route")
        route: str = route_obj.path if route_obj is not None else path

        # Parse headers into a lowercase dict for convenient access.
        raw_scope_headers: list[tuple[bytes, bytes]] = list(scope.get("headers", []))
        header_map: dict[str, str] = {
            k.decode("latin-1").lower(): v.decode("latin-1")
            for k, v in raw_scope_headers
        }

        user_agent: str = header_map.get("user-agent", "")
        # Prefer X-Forwarded-For (set by load balancers) over raw client IP.
        client_ip: str = header_map.get("x-forwarded-for", "")
        if not client_ip:
            raw_client = scope.get("client")
            client_ip = raw_client[0] if raw_client else ""

        # Propagate existing session or generate a new one.
        session_id: str = header_map.get("x-session-id", str(uuid.uuid4()))

        base_labels: dict[str, str] = {
            "http.method": method,
            "http.route": route,
            "http.scheme": scheme,
        }

        # Mutable state captured by the send interceptor closure.
        status_code: int = 0
        response_body_size: int = 0

        async def send_with_telemetry(message: ASGIMessage) -> None:
            """Intercept ASGI send to capture status code and inject session header."""
            nonlocal status_code, response_body_size
            if message["type"] == "http.response.start":
                status_code = int(message.get("status", 200))
                outgoing_headers: list[tuple[bytes, bytes]] = list(
                    message.get("headers", [])
                )
                has_session = any(
                    k.lower() == b"x-session-id" for k, _ in outgoing_headers
                )
                if not has_session:
                    outgoing_headers.append(
                        (b"x-session-id", session_id.encode("ascii"))
                    )
                    message = {**message, "headers": outgoing_headers}
            elif message["type"] == "http.response.body":
                body: bytes = message.get("body") or b""
                response_body_size += len(body)
            await send(message)

        instr = self._instruments
        instr["active_requests"].add(1, base_labels)
        t_start = time.perf_counter()

        with get_tracer().start_as_current_span(f"HTTP {method} {route}") as span:
            span.set_attribute("http.method", method)
            span.set_attribute("http.target", path)
            span.set_attribute("http.route", route)
            span.set_attribute("http.scheme", scheme)
            span.set_attribute("http.user_agent", user_agent)
            span.set_attribute("net.host.name", host)
            span.set_attribute("http.client_ip", client_ip)
            span.set_attribute("app.session_id", session_id)

            try:
                await self._app(scope, receive, send_with_telemetry)
            except Exception as exc:
                duration_s = time.perf_counter() - t_start
                instr["active_requests"].add(-1, base_labels)
                err_labels = {**base_labels, "http.status_code": "500"}
                instr["request_count"].add(1, err_labels)
                instr["request_duration"].record(duration_s, err_labels)
                instr["error_count"].add(1, err_labels)
                span.set_status(StatusCode.ERROR, str(exc))
                _logger.error(
                    "HTTP %s %s — unhandled exception after %.3fs: %s",
                    method,
                    path,
                    duration_s,
                    exc,
                    exc_info=True,
                )
                raise

            duration_s = time.perf_counter() - t_start
            instr["active_requests"].add(-1, base_labels)

            response_labels = {**base_labels, "http.status_code": str(status_code)}
            instr["request_count"].add(1, response_labels)
            instr["request_duration"].record(duration_s, response_labels)
            instr["response_size"].record(response_body_size, response_labels)

            span.set_attribute("http.status_code", status_code)

            if status_code >= 400:
                span.set_status(StatusCode.ERROR)
                instr["error_count"].add(1, response_labels)
            else:
                span.set_status(StatusCode.OK)

            ctx = span.get_span_context()
            trace_id = (
                format(ctx.trace_id, "032x") if ctx and ctx.is_valid else "0" * 32
            )
            log_level = logging.WARNING if status_code >= 400 else logging.INFO
            _logger.log(
                log_level,
                "HTTP %s %s → %d (%.3fs) trace=%s session=%s",
                method,
                path,
                status_code,
                duration_s,
                trace_id,
                session_id,
            )
