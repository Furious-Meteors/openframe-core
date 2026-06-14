# ADR-005 — Middleware Must Not Call setup_telemetry()

**Status:** Accepted — v1.0.0

---

**Chosen:** `TelemetryMiddleware` calls `get_tracer()` and `get_meter()` directly. It never calls `setup_telemetry()`. Application startup (a `lifespan` handler) is the only place `setup_telemetry()` is called.

**Rejected:** `TelemetryMiddleware` calling `setup_telemetry()` on first request "to be safe".

**Why:** The OTel SDK protects `trace.set_tracer_provider()` and `metrics.set_meter_provider()` with a `Once` guard — the first call per process succeeds; all subsequent calls are silently rejected. If `TelemetryMiddleware` calls `setup_telemetry()` on the first HTTP request, it overwrites the `TracerProvider` that was set by the application's `lifespan` handler at startup. In testing, this overwrites the `InMemorySpanExporter` provider installed by `conftest.py`, causing every span assertion to fail silently — `span_exporter.get_finished_spans()` returns an empty list even when spans were created.

The failure mode is silent and extremely difficult to debug — the middleware produces no error, the spans are simply dropped.

**Consequences:** Every template using `TelemetryMiddleware` must call `setup_telemetry()` in its `lifespan` handler before the first request is served. This is documented in the middleware class docstring and enforced by the test suite — tests that install their own `TracerProvider` via fixtures verify that the middleware uses the fixture's provider rather than reinitialising.
