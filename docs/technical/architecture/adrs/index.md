# Architecture Decision Records

Architecture Decision Records (ADRs) capture significant design choices, the alternatives considered, and the rationale for the decision taken. They are immutable historical records — once accepted, an ADR is never edited; superseded decisions reference the newer ADR.

---

| ADR | Status | Title |
|---|---|---|
| [ADR-001](adr-001-namespace.md) | Accepted — v1.0.0 | Python Namespace Package for `openframe.*` |
| [ADR-002](adr-002-hexagonal.md) | Accepted — v1.0.0 | Hexagonal Architecture as the Universal Spine |
| [ADR-003](adr-003-async.md) | Accepted — v1.0.0 | Async-first Port Contracts |
| [ADR-004](adr-004-pydantic.md) | Accepted — v1.0.0 | Pydantic Settings for Adapter Configuration |
| [ADR-005](adr-005-middleware.md) | Accepted — v1.0.0 | Pure ASGI Middleware for Telemetry |
| [ADR-006](adr-006-unified-port-lifecycle.md) | Accepted — v3.0.0 | Unified Port + Lifecycle Contract (supersedes port/health/plugin portions of ADR-002) |

---

## Reading Order

- Start with [ADR-002](adr-002-hexagonal.md) for the overall hexagonal architecture rationale.
- Read [ADR-006](adr-006-unified-port-lifecycle.md) to understand what changed in v3.0.0 and why — it supersedes the port, health, and plugin sections of ADR-002.
- [ADR-001](adr-001-namespace.md), [ADR-003](adr-003-async.md), [ADR-004](adr-004-pydantic.md), and [ADR-005](adr-005-middleware.md) are independent and can be read in any order.
