# Telemetry Export Failing

Traces and metrics are not appearing in the OTel backend (Grafana Cloud, Honeycomb, Datadog). The service is otherwise healthy.

---

## Symptoms

- No new spans in the tracing backend
- Metric dashboards show no data since a specific time
- `OTEL_EXPORTER_OTLP_ENDPOINT` is set but nothing is exported
- No errors in application logs about telemetry (the OTel SDK swallows export errors by default)

---

## Diagnosis

**1. Verify the endpoint and headers are set.**

```bash
modal app logs <app-name> | grep "OpenTelemetry SDK initialised"
```

`no-op mode` in that log line means `OTEL_EXPORTER_OTLP_ENDPOINT` is missing or empty.

**2. Test the OTLP endpoint directly.**

```bash
curl -v -H "Authorization: Basic <token>" \
  https://<your-endpoint>/v1/traces \
  -d '{"resourceSpans": []}' \
  -H "Content-Type: application/json"
```

A 200 or 202 means the endpoint is reachable and the auth is correct. A 401 means the token is wrong. A connection error means the URL is wrong.

**3. Check if setup_telemetry() was called.**

`setup_telemetry()` must be called in the `lifespan` handler before the first request. If it was never called, `get_tracer()` returns a no-op tracer and no spans are created.

---

## Recovery

**Missing or wrong env vars:**

```bash
modal secret update openframe-otel \
  OTEL_EXPORTER_OTLP_ENDPOINT=https://your-endpoint \
  OTEL_EXPORTER_OTLP_HEADERS="Authorization=Basic <token>"
modal deploy modal_app.py
```

**setup_telemetry() not called:**

Add `setup_telemetry()` to the `lifespan` handler in `modal_app.py` or the FastAPI app startup event. Redeploy.
