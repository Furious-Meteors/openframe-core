# openframe-core

The foundation package of the OpenFrame Microservice Development Suite — the unified port + lifecycle contract layer, structured exceptions, telemetry, and ASGI middleware for any hexagonal architecture Python service. Every ecosystem package pins `openframe-core>=3.0,<4`.

> **v3.0.0 is a breaking redesign.** The old lifecycle-free ports, standalone `HealthCheck`, and separate `OpenFramePlugin` protocol are replaced by a single unified contract layer (`BasePort` = `Identity` + `Lifecycle`). The error hierarchy is consolidated under `OpenFrameError`. **v3.1.0 merges `openframe.core.contracts` into `openframe.core.ports`** and moves the outbound protocols into an internal `ports/outbound/` sub-module — no compatibility shim, no public API change. See [ADR-006](technical/architecture/adrs/adr-006-unified-port-lifecycle.md) for the full rationale.

---

## Developer Guide

| Section | Contents |
|---|---|
| [Quick Start](developer-guide/quick-start/index.md) | Working integration in 5 minutes |
| [How It Works](developer-guide/how-it-works.md) | Hexagonal architecture in plain language |
| [First Code Change](developer-guide/first-change.md) | Smallest meaningful change to the package |
| [Debugging Guide](developer-guide/debugging.md) | OpenFrameError traces, OTel spans, common failures |


## Technical Documentation

| Section | Contents |
|---|---|
| [System Overview](technical/overview/system-overview.md) | What the package does, unified contract layer, key design properties |
| [Architecture](technical/architecture/system-architecture.md) | Module dependency DAG, both sides of the hexagon |
| [Package Journey](technical/architecture/package-journey/index.md) | How a request moves from registry wiring through adapter to response |
| [ADRs](technical/architecture/adrs/index.md) | Six architectural decision records from the design and review process |
| [Capability Taxonomy](technical/architecture/capability-taxonomy.md) | The `Capability` enum reference |
| [Error Taxonomy](technical/architecture/error-taxonomy.md) | The `OpenFrameError` hierarchy and `domain.kind` code convention |
| [Infrastructure](technical/infrastructure/platform.md) | Modal platform, devpi registry, GitHub Actions |
| [Deployment](technical/deployment/environments.md) | Environments, secrets, CI/CD pipeline |
| [Operations](technical/operations/index.md) | Monitoring, runbooks for six failure scenarios |

## Code Documentation

| Section | Contents |
|---|---|
| [Getting Started](code/getting-started/index.md) | Install, configure, smoke test |
| [Modules](code/modules/index.md) | Function and class reference for all core modules |
| [CI/CD](code/cicd/pipeline.md) | GitHub Actions workflows |
