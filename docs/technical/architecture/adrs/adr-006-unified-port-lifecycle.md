# ADR-006 — Unified Port + Lifecycle Contract

**Status:** Accepted — v3.0.0
**Supersedes:** the port/health/plugin portions of [ADR-002 — Hexagonal Architecture as the Universal Spine](adr-002-hexagonal.md) and the "seven-module" framing it implied.

---

## Context

`openframe-core` v1.0–v2.0 grew three separate, disconnected contract families:

1. **`ports/`** — `BaseRepository[T]`, `BaseProducer[T]`, `BaseConsumer[T]`. Hardcoded, structural `Protocol`s with domain methods only. No `name`, no `version`, no `initialize`/`shutdown`, no way to ask "is this thing healthy" without a second, unrelated protocol.
2. **`health/`** — `HealthCheck`, a standalone `Protocol` with `ping()`/`is_ready()`. Adapters that wanted both a port and a health check had to satisfy two unrelated structural protocols with no shared vocabulary (`ping`/`is_ready` vs. nothing).
3. **`plugins/contracts.py`** — `OpenFramePlugin`, a *third*, independent `Protocol` with `name`/`version`/`capability` + `initialize`/`shutdown`/`health()` returning `PluginHealth`. This is the protocol the plugin registry actually operates on. Adapters that wanted to be both a `BaseRepository` **and** participate in the plugin registry had to hand-write a wrapper class satisfying `OpenFramePlugin` that delegated to the "real" port object — the "plugin wrapper tax" observed first-hand in `openframe-adapters-queue-kafka`'s `KafkaPlugin` wrapper around its own producer/consumer.

Three contract families for what is conceptually one idea — "a thing with an identity, that can be started, stopped, and asked if it's healthy, and that does some domain-specific work" — is unnecessary duplication. It also means capability lookups in the registry are keyed on a raw `str` (`plugin.capability == "persistence"`), with no static or runtime guarantee that adapters agree on the vocabulary.

The driving side of the hexagon (use cases, command/query handlers invoked by inbound adapters — HTTP routes, message handlers, CLI commands) had no first-class representation at all. `openframe-core` only modeled the driven/outbound side (`ports/`).

## Decision

Replace all three contract families with **one unified contract layer**, `openframe/core/contracts/` (merged into `openframe/core/ports/` in v3.1.0 — see the addendum below), built from two small, composable primitives:

- **`Identity`** — `name: str`, `version: str`, `capability: Capability`. What a thing *is*.
- **`Lifecycle`** — `async initialize(context: PluginContext) -> None`, `async shutdown() -> None`, `async health() -> PluginHealth`. How a thing is *managed*. `health()` is the single, canonical health primitive — it absorbs the old `HealthCheck.ping()` (cheap liveness) and `HealthCheck.is_ready()` (full readiness) into one call that returns a rich `PluginHealth` snapshot (`PluginStatus` + message + details) instead of two independent bare `bool`s. An adapter that wants to distinguish liveness from readiness encodes that distinction in `PluginStatus` and `PluginHealth.details`, not in a second method.
- **`BasePort(Identity, Lifecycle, Protocol)`** — `@runtime_checkable`. The single outbound base every port extends. **Every port is lifecycle-aware by definition** — there is no lifecycle-free port and no `Managed*` twin of a lifecycle-aware one. `BaseRepository[T]`, `BaseProducer[T]`, and `BaseConsumer[T]` are rebuilt in place as `BasePort` plus their own domain methods (`Protocol[T]` combined with `BasePort`).
- **`Capability(str, Enum)`** — a closed, typed taxonomy (`PERSISTENCE`, `CACHE`, `QUEUE`, `SECRETS`, `FLAGS`, `STORAGE`, `TRANSPORT`, `INFERENCE`, `EMBEDDING`, `SCHEDULE`, `SEARCH`) replacing raw `str` capability keys. Registry lookups (`PluginRegistry.get`/`get_all`) take a `Capability` member, not a string. This gives IDEs, type-checkers, and code review a closed, discoverable vocabulary instead of adapters inventing ad hoc capability strings.

A "plugin" is no longer a distinct concept with its own protocol — **a plugin is just a registered `BasePort`.** There is nothing beyond `BasePort` to satisfy to participate in the registry. The wrapper tax this ADR eliminates: an adapter that is already a `BaseRepository`/`BaseProducer`/`BaseConsumer` needs zero additional code to also be a registrable plugin, because those ports *are* `BasePort`s.

The driving side of the hexagon gets first-class treatment in a new `openframe/core/inbound/` module: `UseCase[TInput, TOutput]`, `CommandHandler[TInput]`, `QueryHandler[TInput, TOutput]`, and `RequestContext` (correlation id + optional `PrincipalContext`/`TenantContext`). Inbound adapters (`TelemetryMiddleware` today, future `protocol`-package entrypoints) construct a `RequestContext` and pass it into a use case's `execute()`. This makes `contracts` the apex of the dependency graph, with both `ports` (outbound) and `inbound` (driving) depending on it — the hexagon now has two visible sides in the DAG, not one.

Identity/tenancy propagation, previously absent, is threaded structurally through the new `context.py`: `PrincipalContext` and `TenantContext` are frozen dataclasses. `PluginContext` (still the argument to `Lifecycle.initialize`) gains optional `principal`/`tenant` fields carrying them, and `RequestContext` (inbound side) carries the same two types. `PluginRegistry.initialize_all()` is updated to actually thread real `config`/`principal`/`tenant` through `PluginContext` instead of the previous hardcoded `config={}`.

### What is removed

- **The hardcoded, lifecycle-free `ports/` protocols.** `BaseRepository`, `BaseProducer`, `BaseConsumer` no longer exist as bare domain-method-only `Protocol`s — they are rebuilt on `BasePort` in place. There is no lifecycle-free version left to import; this is not an additive change.
- **The standalone `HealthCheck` protocol and the entire `health/` package** (`health/protocol.py`, `health/__init__.py`). `ping()`/`is_ready()` are gone. Health is exclusively `Lifecycle.health() -> PluginHealth`.
- **`OpenFramePlugin` as a separate protocol.** `plugins/contracts.py` no longer defines its own duplicate `Identity`/`Lifecycle`-shaped protocol. `PluginStatus`, `PluginHealth`, and `PluginContext` move to `contracts/health.py` — the one canonical home — and `plugins/contracts.py` is deleted outright (see "Alternatives considered" below for why deletion was chosen over a re-export shim). All internal callers (`plugins/__init__.py`, `plugins/registry.py`, `runtime/bootstrap.py`) import `BasePort` and the `contracts` types directly.

There are no deprecated aliases and no backward-compatible shims for any of the above. This is an intentional, full clean break (see "Compatibility" below).

## Consequences

- **Dependency DAG changes.** `contracts` becomes the apex module (after `exceptions → config`). Both `ports` and the new `inbound` module depend on `contracts`; `plugins` also depends on `contracts` directly (not through a `plugins/contracts.py` duplicate). `telemetry → tracing → middleware` is unaffected and remains a separate chain also rooted at `contracts` (inbound adapters like `TelemetryMiddleware` construct `RequestContext` from `contracts.context` types). The `health` node is gone entirely — it was never a separate concern, only ever a subset of `Lifecycle`. See [system-architecture.md](../system-architecture.md) for the updated DAG diagram.
- **Every port gains lifecycle.** Any adapter implementing `BaseRepository`/`BaseProducer`/`BaseConsumer` must now also implement `name`, `version`, `capability`, `initialize`, `shutdown`, `health`. This is the intended breaking change — adapters that were previously "just a port" become plugin-registrable for free, at the cost of implementing five more members. `openframe-adapters` packages migrate on their own schedule because of the major version pin (see below).
- **Capability lookups become type-safe.** `PluginRegistry.get(Capability.PERSISTENCE)` replaces `PluginRegistry.get("persistence")`. Typos that previously produced a silent, hard-to-debug `KeyError` at runtime are now caught by static type checkers before the code ships.
- **`PluginRegistry.get()` is strict.** Because `Capability` lookups are now type-safe and because silently returning the first of several same-capability ports hides configuration mistakes, `get()` raises when more than one `BasePort` is registered under the requested capability (use `get_all()` for the deliberate multi-adapter case, e.g. a primary + replica persistence pair). This is a new, stricter guarantee that did not exist for the old string-keyed lookup.
- **Contract test suites are restructured around `BasePort`.** `testing/contracts/port.py` (`PortContractTests`) and `testing/contracts/lifecycle.py` (`LifecycleContractTests`) become the shared base every port-specific contract-test class (`RepositoryContractTests`, `ProducerContractTests`, `ConsumerContractTests`) builds on, replacing the old ad hoc `test_satisfies_health_check_protocol` block. `testing/fakes/*` (`InMemoryRepository`, `FakeProducer`, `FakeConsumer`) are updated to satisfy `BasePort` — they gain `name`/`version`/`capability` and `initialize`/`shutdown`/`health`, and lose `ping`/`is_ready`.
- **Downstream compatibility is intentionally broken.** No deprecated aliases exist for `HealthCheck`, `OpenFramePlugin`, or the pre-v3 lifecycle-free ports. Version bumps `2.0.0` → `3.0.0` in `pyproject.toml`. Because `openframe-adapters` packages pin `openframe-core` with `>=2.0,<3`, they will **not** auto-resolve to v3 and will continue to function against v2.x until they are explicitly migrated to the new contract layer in their own repository (out of scope for this change — see the plan's "Out of scope" section).

## Alternatives considered

- **Keep `plugins/contracts.py` as a re-export shim** (`from openframe.core.contracts import ...` re-exported under the old names) instead of deleting it outright. Rejected: ADR-006's own principle is "one contract family, one canonical home per concept." A re-export module is a second import path for the exact same type with no behavioral difference — it adds a file to maintain and a decision point for every future contributor ("do I import from `contracts` or `plugins.contracts`?") for zero benefit, since this is a deliberate breaking major version with no compatibility promise to preserve. Full deletion is more consistent with "no dual/back-compat approach."
- **Keep two health methods (`ping`/`is_ready`) on `Lifecycle`** instead of collapsing to one `health()`. Rejected: the two-level distinction is a *reporting granularity* concern, not a *protocol shape* concern — it is fully expressible as `PluginStatus` values and `PluginHealth.details` (e.g. `PluginHealth(status=PluginStatus.READY, details={"ping_ms": 2.1, "schema_ok": True})`) without needing two methods on every implementer.
- **Model `Capability` as an open `str` subtype (`NewType` or plain constants module)** instead of a closed `Enum`. Rejected: the plan explicitly calls for a typed enum, and a closed enum is what makes `PluginRegistry.get_all()`'s duplicate-guard and static analysis of "which capabilities exist" possible. Extending the taxonomy in a later minor version is a backward-compatible additive change (new enum member), consistent with normal enum evolution.

---

## Addendum — Unified error hierarchy (v3.0.0)

The same "one contract family, one canonical home" principle applied to ports
is applied to exceptions in this release.

### Context

Errors were split across two packages: `exceptions/` (`AdapterError` family)
and `errors/` (`PluginError` family). Neither shared a common root, so there
was no single catch point for "anything openframe raised," and the two package
names (`exceptions` vs `errors`) were an arbitrary split for what are
conceptually siblings.

### Decision

- **Consolidate into a single `exceptions/` package.** `errors/` is deleted.
  The package keeps the ecosystem-pinned `openframe.core.exceptions` import
  path (only the newer plugin-error path moves), and `exceptions/` is the
  lowest layer of the DAG, so the shared root can live there without inverting
  any dependency.
- **`OpenFrameError` root.** A single root every family derives from
  (`AdapterError`, `PluginError`, and every downstream package's family), so
  `except OpenFrameError` is a catch point for the whole ecosystem. It carries
  `code`, `message`, `severity`, `retryable`, `correlation_id`, `context`, and
  `cause` — semantics carried as **data** so upper layers reason over them
  without an `isinstance` ladder.
- **Typed, decentralised taxonomy.** `ErrorCode`/`Severity` are `StrEnum`s;
  codes follow a `domain.kind` convention. `ErrorCode` enumerates only core's
  codes — downstream packages declare their own plain-string codes rather than
  extending the enum, so the taxonomy grows without a central bottleneck.
- **Constructors preserved.** `AdapterError(message, adapter, operation, cause)`
  and `PluginError(message, plugin_name)` keep their exact signatures and
  `__str__`, so existing raise sites and `except` clauses are unchanged. Each
  subclass sets its `code` (and, where meaningful, `retryable`) as a class
  attribute.
- **Errors flow into telemetry without importing it.** `exceptions` stays at
  the bottom of the DAG and imports nothing upward. `telemetry.record_error`
  (which legally imports `OpenFrameError`) reads the error's data and records
  it — span attributes (`error.code`/`severity`/`retryable`), the exception
  event, a `correlation_id` stamp-back, and a deduped `openframe.error.count`
  metric. It is called at each boundary seam (`TracingProxy`,
  `TelemetryMiddleware`, `PluginRegistry` lifecycle). See
  [error-taxonomy.md](../error-taxonomy.md) for the full reference.

### Deferred

- `to_dict()`/`from_dict()` serialisation for cross-service propagation. The
  fields are laid out to be serialisation-ready; the methods are added when the
  `protocol`/`client` packages need them (a non-breaking addition).

---

## Addendum — contracts/ merged into ports/, outbound/ sub-module introduced (v3.1.0)

### Context

`openframe.core.contracts` (the port/lifecycle primitives: `Identity`,
`Lifecycle`, `BasePort`, `Capability`, `PluginStatus`/`PluginHealth`/
`PluginContext`, `PrincipalContext`/`TenantContext`) and
`openframe.core.ports` (the outbound protocols: `BaseRepository`,
`BaseProducer`, `BaseConsumer`) were two directories for what this ADR
already establishes as one concept — the port contract layer of the
hexagonal architecture. Every outbound protocol extends `BasePort`
directly; keeping the primitives and the protocols that compose them in
two separate top-level modules was an arbitrary split, not a meaningful
boundary.

Separately, `BaseRepository`/`BaseProducer`/`BaseConsumer` are
capability-specific outbound port protocols — what you get when the
`BasePort` primitives are applied to one outbound capability. They are
not implementations (those live in `openframe-adapters`), and sitting
as three loose files directly inside `ports/` gave them no distinct
identity from the primitive modules they are built on, and no clear
intake point for future capability-specific protocols
(`BaseSecretsProvider`, `BaseObjectStore`, `BaseFeatureFlagProvider`
from `openframe-infra`).

### Decision

- **Merge `contracts/` into `ports/`.** All six primitive modules
  (`capability.py`, `context.py`, `health.py`, `identity.py`,
  `lifecycle.py`, `port.py`) move into `openframe/core/ports/`. A single
  `ports/__init__.py` exports everything previously split across the two
  `__init__.py` files.
- **Introduce `ports/outbound/`.** The three existing outbound protocol
  modules (`repository.py`, `producer.py`, `consumer.py`) move into a new
  `openframe/core/ports/outbound/` sub-package, mirroring the existing
  `openframe/core/inbound/` on the driving side of the hexagon. The name
  `outbound/` (not `protocols/`, not `implementations/`) matches the
  hexagonal vocabulary already in use, gives a clear intake rule for
  future capability-specific outbound protocols, and is honest about
  what these are — port contracts, not implementations.
- **No compatibility shim.** Consistent with this ADR's "one contract
  family, one canonical home per concept" principle (see "Alternatives
  considered" above), `openframe/core/contracts/` is deleted outright —
  no re-export module is left at the old path.
- **No class is renamed and no method signature changes.** This is a
  pure structural rename and merge; every name importable from
  `openframe.core.contracts` before v3.1.0 is importable from
  `openframe.core.ports` after it. `BaseRepository`, `BaseProducer`, and
  `BaseConsumer` remain importable from the top-level
  `openframe.core.ports` package — the `outbound/` sub-module is an
  internal reorganisation, not a public API change.

### Consequences

- **Dependency DAG simplifies.** `ports` is now the single apex module
  (after `exceptions → config`) that `inbound` and `plugins` depend on
  directly, rather than both depending on a separate `contracts` module
  that `ports` also depended on. Within `ports/`, the six primitive
  modules form one linear chain and the three `ports/outbound/` modules
  each depend only on `ports/port` — a clean two-tier structure, not a
  new cycle.
- **`ports/outbound/` has a stated intake rule.** Any future
  capability-specific outbound port protocol belongs in
  `ports/outbound/`, re-exported from `ports/__init__.py` — not as a
  new top-level `ports/` module, and not defined inside the downstream
  package that first needs it. See
  [capability-taxonomy.md](../capability-taxonomy.md#where-capability-specific-outbound-port-protocols-live).
- **Shipped as a minor version, not a major one.** Version bumps
  `3.0.1` → `3.1.0` in `pyproject.toml` — this is judged a structural
  reorganisation of the v3.0.0 contract layer rather than a further
  architectural change, so it does not warrant its own major version.
  Unlike the v3.0.0 break, `openframe-adapters` and other ecosystem
  packages pinned `openframe-core>=3.0,<4` **will** auto-resolve to
  3.1.0 on their next install. Because there is still no compatibility
  shim at the old `openframe.core.contracts` path, any package importing
  from it will fail immediately on upgrade — downstream packages still
  importing `openframe.core.contracts` must migrate to
  `openframe.core.ports` before taking a `openframe-core` upgrade past
  3.1.0, even though semver alone would not have warned them.
