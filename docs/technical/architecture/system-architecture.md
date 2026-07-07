# System Architecture

`openframe-core` is a pure Python foundation package built around a unified
port + lifecycle contract layer (ADR-006). `contracts/` is the apex module
— every other module depends on it, directly or transitively — and both
the outbound (`ports`) and inbound (`inbound`) sides of the hexagon are
first-class citizens of the dependency graph. No module imports from a
module higher in the chain.

---

## Module Dependency DAG

Every arrow in this diagram is a permitted import direction. No reverse
imports exist. There is no standalone `health` node — health is a member
of `contracts` (`Lifecycle.health()` + `PluginHealth`). There is no
standalone `errors` node either — the whole error hierarchy (the adapter
family and the plugin family) lives in the single `exceptions` package,
rooted at `OpenFrameError`. `telemetry` imports `exceptions` so its
`record_error` seam can read an error's structured data without the error
ever importing telemetry.

```mermaid
flowchart LR
    EX["exceptions"]
    CF["config"]
    CO["contracts"]
    PO["ports"]
    IN["inbound"]
    TE["telemetry"]
    TR["tracing"]
    MW["middleware"]
    PL["plugins"]
    RT["runtime"]
    TS["testing"]

    EX --> CF --> CO
    EX --> TE
    CO --> PO
    CO --> IN
    CO --> TE --> TR --> MW
    CO --> PL --> RT
    TE --> PL
    CO --> TS

    style EX fill:#1a1a1a,color:#F0F0F0,stroke:#6DB33F
    style CF fill:#1a1a1a,color:#F0F0F0,stroke:#6DB33F
    style CO fill:#1a1a1a,color:#8CC63F,stroke:#6DB33F
    style PO fill:#141414,color:#F0F0F0,stroke:#4E8A2A
    style IN fill:#141414,color:#F0F0F0,stroke:#4E8A2A
    style TE fill:#141414,color:#F0F0F0,stroke:#4E8A2A
    style TR fill:#141414,color:#F0F0F0,stroke:#4E8A2A
    style MW fill:#141414,color:#F0F0F0,stroke:#4E8A2A
    style PL fill:#141414,color:#F0F0F0,stroke:#4E8A2A
    style RT fill:#141414,color:#F0F0F0,stroke:#4E8A2A
    style TS fill:#141414,color:#F0F0F0,stroke:#4E8A2A
```

See [ADR-006](adrs/adr-006-unified-port-lifecycle.md) for the full
rationale, and [capability-taxonomy.md](capability-taxonomy.md) for the
`Capability` enum reference.

---

## Module Inventory

| Module | Public exports | External deps |
|---|---|---|
| `exceptions` | `OpenFrameError` (root), `ErrorCode`, `Severity`, `AdapterError` + 5 subclasses, `PluginError` + 4 subclasses (incl. `AmbiguousCapabilityError`) | none |
| `config` | `BaseAdapterSettings` | `pydantic-settings` |
| `contracts` | `Identity`, `Lifecycle`, `BasePort`, `Capability`, `PluginStatus`, `PluginHealth`, `PluginContext`, `PrincipalContext`, `TenantContext` | none |
| `ports` | `BaseRepository[T]`, `BaseProducer[T]`, `BaseConsumer[T]` (each `BasePort` + domain methods) | none |
| `inbound` | `UseCase[TIn, TOut]`, `CommandHandler[TIn]`, `QueryHandler[TIn, TOut]`, `RequestContext` | none |
| `telemetry` | `setup_telemetry`, `get_tracer`, `get_meter`, `record_lifecycle_event`, `record_error` | `opentelemetry-*` |
| `tracing` | `TracingProxy` | `opentelemetry-api` |
| `middleware` | `TelemetryMiddleware`, `ASGIScope`, `ASGIMessage`, `Receive`, `Send`, `ASGIApp` | `opentelemetry-api` |
| `plugins` | `PluginRegistry` (+ re-exports of `contracts` types) | none |
| `runtime` | `ApplicationBootstrap` | none |
| `testing` | `InMemoryRepository`, `FakeProducer`, `FakeConsumer`, `LifecycleContractTests`, `PortContractTests`, `RepositoryContractTests`, `ProducerContractTests`, `ConsumerContractTests` | none |

---

## The Hexagon, Explicitly

`contracts` sits at the apex. Two sibling modules hang off it, one per side
of the hexagon:

- **`ports`** — the outbound/driven side. Every port (`BaseRepository`,
  `BaseProducer`, `BaseConsumer`) is `BasePort` (`Identity` + `Lifecycle`)
  plus its own domain methods. Adapters implement these structurally.
- **`inbound`** — the driving side. `UseCase`/`CommandHandler`/`QueryHandler`
  are invoked by inbound adapters (HTTP routes via `TelemetryMiddleware`,
  message handlers, CLI commands) with a `RequestContext` carrying a
  correlation id and optional identity.

`plugins.PluginRegistry` operates directly on `BasePort` — there is no
separate plugin protocol. A "plugin" is just a registered `BasePort`.

---

## How a Template Uses openframe-core

The following sequence shows how a FastAPI template wires `openframe-core`
at startup and serves a request.

```mermaid
sequenceDiagram
    participant L as lifespan handler
    participant D as deps.py
    participant Reg as PluginRegistry
    participant TP as TracingProxy
    participant R as PostgresRepository
    participant MW as TelemetryMiddleware

    L->>L: setup_telemetry()
    L->>D: build_repository()
    D->>R: PostgresRepository(settings)
    D->>Reg: registry.register(repo, config=pg_config)
    Reg->>R: repo.initialize(PluginContext)
    D->>TP: TracingProxy(repo, "repository.item")
    D-->>L: traced, initialized repository ready

    Note over MW: every HTTP request
    MW->>MW: start span "HTTP GET /items/{id}"
    MW->>D: registry.get(Capability.PERSISTENCE) → TracingProxy
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

`openframe-core` is a library — it has no runtime process. It is installed
as a dependency inside a Modal function container (or any other Python
environment) and runs in-process with the application.

```mermaid
flowchart TD
    PyPI["PyPI\nopenframe-core 3.0.0"]
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
