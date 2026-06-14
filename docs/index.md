# openframe-core

The foundation package of the OpenFrame Microservice Development Suite — ports, tracing, telemetry, exceptions, config, and ASGI middleware for any hexagonal architecture Python service.

---

## Developer Guide

| Section | Contents |
|---|---|
| [Quick Start](developer-guide/quick-start/index.md) | Working integration in 5 minutes |
| [How It Works](developer-guide/how-it-works.md) | Hexagonal architecture in plain language |
| [First Code Change](developer-guide/first-change.md) | Smallest meaningful change to the package |
| [Debugging Guide](developer-guide/debugging.md) | AdapterError traces, OTel spans, common failures |


## Technical Documentation

| Section | Contents |
|---|---|
| [System Overview](technical/overview/system-overview.md) | What the package does, seven-module model, key design properties |
| [Architecture](technical/architecture/system-architecture.md) | Module design, dependency order, data flows, design decisions |
| [Package Journey](technical/architecture/package-journey/index.md) | How a request moves from template wiring through adapter to response |
| [ADRs](technical/architecture/adrs/adr-001-namespace.md) | Five architectural decision records from the design and review process |
| [Infrastructure](technical/infrastructure/platform.md) | Modal platform, devpi registry, GitHub Actions |
| [Deployment](technical/deployment/environments.md) | Environments, secrets, CI/CD pipeline |
| [Operations](technical/operations/index.md) | Monitoring, runbooks for six failure scenarios |

## Code Documentation

| Section | Contents |
|---|---|
| [Getting Started](code/getting-started/index.md) | Install, configure, smoke test |
| [Modules](code/modules/index.md) | Function and class reference for all seven core modules |
| [CI/CD](code/cicd/pipeline.md) | GitHub Actions workflows |
