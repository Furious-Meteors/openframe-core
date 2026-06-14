# System Architecture

`openframe-core` is a pure Python foundation package organised into seven modules with a strict one-way dependency order. No module imports from a module higher in the chain.

---

## Module Dependency DAG

Every arrow in this diagram is a permitted import direction. No reverse imports exist.

```mermaid
flowchart LR
    EX["exceptions"]
    CF["config"]
    PO["ports"]
    HE["health"]
    TE["telemetry"]
    TR["tracing"]
    MW["middleware"]

    EX --> CF --> PO --> HE --> TE --> TR --> MW

    style EX fill:#1a1a1a,color:#F0F0F0,stroke:#6DB33F
    style CF fill:#1a1a1a,color:#F0F0F0,stroke:#6DB33F
    style PO fill:#1a1a1a,color:#F0F0F0,stroke:#6DB33F
    style HE fill:#141414,color:#F0F0F0,stroke:#4E8A2A
    style TE fill:#141414,color:#F0F0F0,stroke:#4E8A2A
    style TR fill:#141414,color:#F0F0F0,stroke:#4E8A2A
    style MW fill:#141414,color:#F0F0F0,stroke:#4E8A2A
```

---

## Module Inventory

| Module | Public exports | External deps |
|---|---|---|
| `exceptions` | `AdapterError` + 5 subclasses | none |
| `config` | `BaseAdapterSettings` | `pydantic-settings` |
| `ports` | `BaseRepository[T]`, `BaseProducer[T]`, `BaseConsumer[T]` | none |
| `health` | `HealthCheck` | none |
| `telemetry` | `setup_telemetry`, `get_tracer`, `get_meter`, `record_lifecycle_event` | `opentelemetry-*` |
| `tracing` | `TracingProxy` | `opentelemetry-api` |
| `middleware` | `TelemetryMiddleware`, `ASGIScope`, `ASGIMessage`, `Receive`, `Send`, `ASGIApp` | `opentelemetry-api` |

---

## How a Template Uses openframe-core

The following sequence shows how a FastAPI template wires `openframe-core` at startup and serves a request.

```mermaid
sequenceDiagram
    participant L as lifespan handler
    participant D as deps.py
    participant TP as TracingProxy
    participant R as PostgresRepository
    participant MW as TelemetryMiddleware

    L->>L: setup_telemetry()
    L->>D: build_repository()
    D->>R: PostgresRepository(settings)
    D->>TP: TracingProxy(repo, "repository.item")
    D-->>L: traced repository ready

    Note over MW: every HTTP request
    MW->>MW: start span "HTTP GET /items/{id}"
    MW->>D: get_repository() → TracingProxy
    D->>TP: repo.get(entity_id)
    TP->>TP: start child span "repository.item.get"
    TP->>R: PostgresRepository.get(entity_id)
    R-->>TP: entity
    TP-->>D: entity
    D-->>MW: entity
    MW->>MW: set span status OK, record metrics
    MW-->>MW: inject x-session-id, emit log
```

---

## Deployment Topology

`openframe-core` is a library — it has no runtime process. It is installed as a dependency inside a Modal function container (or any other Python environment) and runs in-process with the application.

```mermaid
flowchart TD
    PyPI["PyPI\nopenframe-core 1.0.0"]
    Container["Modal function container\npip install openframe-core"]
    App["FastAPI application\nfrom openframe.core.* import ..."]
    OTel["OTLP endpoint\nGrafana Cloud / Honeycomb / Datadog"]

    PyPI --> Container
    Container --> App
    App -->|traces + metrics| OTel

    style PyPI fill:#1a1a1a,color:#F0F0F0,stroke:#6DB33F
    style Container fill:#141414,color:#F0F0F0,stroke:#4E8A2A
    style App fill:#1a1a1a,color:#8CC63F,stroke:#6DB33F
    style OTel fill:#141414,color:#F0F0F0,stroke:#4E8A2A
```
