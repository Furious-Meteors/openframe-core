# Modal Cold Start Spike

Cold starts are spiking — new Modal containers are starting frequently, causing high `lifecycle.cold_start` metric values and intermittent latency spikes on first requests.

---

## Symptoms

- `lifecycle.cold_start` counter increases rapidly in metrics
- First-request latency spikes (> 2s) visible in `http.server.request.duration` histogram
- Modal dashboard shows frequent container restarts
- No application errors — subsequent requests to the same container are fast

---

## Diagnosis

**1. Identify the cause of container cycling.**

```bash
modal app logs <app-name> | grep "cold_start\|container\|start"
```

Containers restart due to: OOM kills, unhandled exceptions in `@enter`, scale-to-zero + scale-out cycles, or Modal infrastructure events.

**2. Check memory usage.**

If containers are OOM-killed, `lifecycle.cold_start` spikes coincide with `lifecycle.oom_kill` events (if recorded). Check Modal dashboard for memory metrics.

**3. Check `setup_telemetry()` timing.**

`setup_telemetry()` is called in `@enter` (the Modal equivalent of `lifespan`). If it throws (e.g. invalid OTLP endpoint), the container may restart in a loop.

---

## Recovery

**OOM kills:** Increase container memory in `modal_app.py`:

```python
@app.function(memory=2048)   # MB
```

**setup_telemetry() crashing:** `setup_telemetry()` is designed to never raise — it degrades to no-op mode and logs a warning. If it is raising, check the OTel SDK version and the `OTEL_EXPORTER_OTLP_ENDPOINT` format.

**Scale-to-zero thrash:** Set `min_containers=1` in `modal_app.py` to keep at least one warm container:

```python
@app.function(min_containers=1)
```

---

## Prevention

Call `record_lifecycle_event("cold_start")` at the top of `@enter`. This populates `lifecycle.cold_start` in metrics and makes cold start frequency visible before it becomes a latency problem.
