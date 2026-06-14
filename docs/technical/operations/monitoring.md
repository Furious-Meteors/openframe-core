# Monitoring

`openframe-core` emits OTel traces and metrics when `OTEL_EXPORTER_OTLP_ENDPOINT` is configured. This page describes what is emitted and what to monitor.

---

## Metrics Emitted by TelemetryMiddleware

| Metric | Type | Unit | Description |
|---|---|---|---|
| `http.server.request.count` | Counter | `1` | Total HTTP requests received |
| `http.server.request.duration` | Histogram | `s` | Request duration in seconds |
| `http.server.active_requests` | UpDownCounter | `1` | Requests currently in flight |
| `http.server.error.count` | Counter | `1` | HTTP 4xx + 5xx responses |
| `http.server.response.size` | Histogram | `By` | Response body size in bytes |

!!! warning
    `http.server.request.duration` uses unit `"s"` (seconds) per OTel HTTP semantic conventions. Any dashboard that ingests this metric name assumes seconds. Do not graph it as milliseconds.

---

## Metrics Emitted by record_lifecycle_event

| Metric | Type | Unit | Description |
|---|---|---|---|
| `lifecycle.<event_name>` | Counter | `1` | Count of named lifecycle events (e.g. `lifecycle.cold_start`) |

---

## Spans

Every async adapter method call via `TracingProxy` produces a child span named `{prefix}.{method_name}`. The root span is `HTTP {method} {route}` from `TelemetryMiddleware`.

Key span attributes to alert on:
- `http.status_code >= 500` — server errors
- `http.server.request.duration > 1.0` — slow requests (threshold per service SLA)
- Span status `ERROR` on non-4xx routes — unexpected failures

---

## Log Format

Every request emits a structured log line:

```
INFO  HTTP GET /items/abc → 200 (0.012s) trace=abc123 session=xyz789
WARN  HTTP GET /items/missing → 404 (0.003s) trace=def456 session=uvw012
```

`WARNING` level for HTTP ≥ 400. `INFO` for 2xx/3xx. Includes `trace_id` and `session_id` for correlation with OTel spans.
