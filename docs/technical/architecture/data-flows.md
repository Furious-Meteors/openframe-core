# Data Flows

How data moves through `openframe-core` components during a request, an adapter operation, and a telemetry export cycle.

---

## HTTP Request Flow

Every inbound HTTP request passes through `TelemetryMiddleware` before reaching the application. The middleware intercepts the ASGI `send` callable to capture the response status code without buffering.

```mermaid
sequenceDiagram
    participant Client
    participant MW as TelemetryMiddleware
    participant App as FastAPI app
    participant OTel as OTel SDK

    Client->>MW: HTTP request (scope, receive, send)
    MW->>MW: generate / propagate x-session-id
    MW->>OTel: start_as_current_span("HTTP GET /items/{id}")
    MW->>MW: active_requests.add(+1)
    MW->>App: await app(scope, receive, send_with_telemetry)
    App-->>MW: response via send_with_telemetry
    MW->>MW: capture status_code from http.response.start
    MW->>MW: inject x-session-id header
    MW->>OTel: set span status (OK / ERROR)
    MW->>OTel: record request_count, request_duration, response_size
    MW->>MW: active_requests.add(-1)
    MW->>MW: emit structured log (INFO / WARNING)
    MW-->>Client: response with x-session-id
```

---

## Adapter Operation Flow

An adapter call flows from the service layer through `TracingProxy` to the real adapter, with `AdapterError` wrapping any driver exception.

```mermaid
sequenceDiagram
    participant SVC as Service layer
    participant TP as TracingProxy
    participant AD as PostgresRepository
    participant DB as asyncpg pool
    participant OTel as OTel SDK

    SVC->>TP: await repo.get(entity_id)
    TP->>OTel: start_as_current_span("repository.item.get")
    TP->>AD: await current_get(entity_id)
    AD->>DB: await pool.fetchrow(query, entity_id)
    alt entity found
        DB-->>AD: row
        AD-->>TP: entity
        TP-->>SVC: entity
    else entity missing
        DB-->>AD: None
        AD-->>TP: raise AdapterNotFoundError
        TP-->>SVC: raise AdapterNotFoundError
    else driver error
        DB-->>AD: asyncpg.PostgresError
        AD-->>TP: raise AdapterQueryError(cause=exc) from exc
        TP-->>SVC: raise AdapterQueryError
    end
    OTel-->>OTel: end span
```

---

## OTel Export Cycle

`openframe-core` configures two exporters at startup. Traces are batched and exported asynchronously; metrics are exported on a periodic interval.

```mermaid
flowchart LR
    App["Application\nget_tracer().start_as_current_span()"]
    BSP["BatchSpanProcessor\nexport_interval default: immediate"]
    OTLP_T["OTLPSpanExporter\n/v1/traces"]
    App2["Application\nget_meter().create_counter()"]
    PMR["PeriodicExportingMetricReader\nexport_interval: OTEL_METRIC_EXPORT_INTERVAL_MS (15 000 ms)"]
    OTLP_M["OTLPMetricExporter\n/v1/metrics"]
    Backend["OTLP backend\nGrafana Cloud / Honeycomb / Datadog"]

    App --> BSP --> OTLP_T --> Backend
    App2 --> PMR --> OTLP_M --> Backend

    style App fill:#1a1a1a,color:#F0F0F0,stroke:#6DB33F
    style App2 fill:#1a1a1a,color:#F0F0F0,stroke:#6DB33F
    style Backend fill:#1a1a1a,color:#8CC63F,stroke:#6DB33F
    style BSP fill:#141414,color:#F0F0F0,stroke:#4E8A2A
    style PMR fill:#141414,color:#F0F0F0,stroke:#4E8A2A
    style OTLP_T fill:#141414,color:#F0F0F0,stroke:#4E8A2A
    style OTLP_M fill:#141414,color:#F0F0F0,stroke:#4E8A2A
```
