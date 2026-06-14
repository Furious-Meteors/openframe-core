# ADR-002 — Hexagonal Architecture as the Universal Spine

**Status:** Accepted — v1.0.0

---

**Chosen:** Every OpenFrame template enforces hexagonal architecture (Ports and Adapters). Business logic in `core/` has zero infrastructure imports. Adapters in `adapters/` implement ports defined in `core/`. `deps.py` is the single assembly point.

**Rejected:** Layered architecture (presentation → service → repository). Traditional layered architectures allow service layers to import repository implementations directly, creating coupling between business logic and infrastructure.

**Why:** Swapping a database, queue, or protocol in a hexagonal architecture requires changing one env var and the wiring in `deps.py`. No business logic changes. This is verifiable — `grep` for infrastructure imports in `src/core/` returns zero results. In a layered architecture, swapping a database typically requires changes throughout the service layer wherever the repository type is referenced.

The hexagonal pattern also makes the test suite faster and more reliable — business logic can be tested with in-memory fakes that satisfy the port Protocol without starting a real database.

**Consequences:** `openframe-core` contains only Protocols (ports) and shared infrastructure abstractions, never concrete adapters. Concrete adapters live in `openframe-adapters-*` packages. This separation is enforced by package boundaries — `openframe-core` has no adapter imports, adapter packages depend on `openframe-core`, not the reverse.
