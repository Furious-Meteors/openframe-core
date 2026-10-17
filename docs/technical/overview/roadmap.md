# Roadmap & Changelog

---

## Roadmap

### openframe-core

Done since this was last updated:

- ~~Establish `ApplicationBootstrap` as the recommended wiring path~~ —
  resolved by consolidating to one class at three levels of ceremony
  (`compose()` → subclass + `configure()` → `.registry` escape hatch)
  instead of three competing patterns. See
  [Design Decisions](../architecture/design-decisions.md) and
  [How It Works § Choosing a Wiring Pattern](../../developer-guide/how-it-works.md#choosing-a-wiring-pattern).
- ~~`test_middleware_types.py`~~ — already existed (147 lines); this item
  was stale.
- ~~Remove redundant `pytest.ini`~~ — already true; no `pytest.ini` exists,
  only `[tool.pytest.ini_options]` in `pyproject.toml`. This item was
  stale.

Documentation tasks:

- (none currently open for `openframe-core` itself — see Lower-priority
  items below)

Lower-priority items:

- Pin OTel SDK dev dependency to exact version — `conftest.py`/`testing/fixtures.py`
  accesses `_TRACER_PROVIDER_SET_ONCE._done` directly; a patch release
  could rename this attribute
- Switch to Trusted Publishing on PyPI — remove `PYPI_API_TOKEN` secret, use OIDC via `pypa/gh-action-pypi-publish`
- Consider whether `PluginNotFoundError`/`PluginInitializationError` should
  actually be raised where their names imply (`PluginRegistry.get()`
  currently raises a plain `KeyError`; `initialize_all()` re-raises the
  original exception unwrapped) — both classes exist in the public
  exception hierarchy but are dead code today. Not done as part of the
  wiring-pattern consolidation since it's a behavioral change, not a
  documentation fix.

### openframe-adapters

Done since this was last updated:

- ~~`openframe-adapters-db-postgres` — first adapter, reference implementation~~
- ~~`openframe-adapters-db-redis` — key-value, pub/sub, semantic cache~~
- ~~`openframe-adapters-db-mongo` — document store for AI Research Vault Phase 1~~
- ~~`openframe-adapters-queue-kafka` — producer + consumer, unlocks event-driven template~~
- ~~Remaining 11 adapters in parallel once the pattern is validated~~ —
  built in checklist-driven waves (see `openframe-adapters`' own
  `.github/CHANGELOG.md`): queue (nats, rabbitmq), relational
  (cockroachdb, mysql, mariadb, oracle), key-value/columnar (dynamodb,
  cassandra), time-series (influxdb), vector (qdrant, milvus, chromadb),
  graph (falkordb). 17 real packages total. FAISS remains explicitly
  descoped — no native id→metadata store, doesn't fit
  `BaseVectorStore`'s id-addressable design.
- ~~`BaseVectorStore[T]` / `BaseGraphStore[T]`~~ — both shipped in this
  repo (v3.5.0 / v3.6.0), each extending `BaseRepository[T]` directly
  plus exactly one new method, rather than as disjoint sibling ports.
  See [ADR-006](../architecture/adrs/adr-006-unified-port-lifecycle.md)
  for the port-design philosophy both followed.

Next capabilities under consideration — each is a candidate NEW
top-level capability, not an extension of an existing adapter package.
**Every adapter in this ecosystem depends only on `openframe-core` plus
its own driver library, never on a sibling `openframe-adapters-*`
package** (e.g. `openframe-adapters-db-falkordb` depends on `redis-py`
directly, not on `openframe-adapters-db-redis`, even though FalkorDB is
Redis-based under the hood) — this constraint applies to every item
below too, most pointedly the Redis-backed ones:

- **Object storage** (`BaseObjectStore` — already named in the v3.1.0
  entry further down this same file) — S3, GCS, Azure Blob, MinIO. Strongest fit for the existing
  extend-`BaseRepository`-plus-one-method pattern; put/get/delete/list
  by key is arguably more naturally CRUD-shaped than graph nodes were.
  **Superseded twice, history kept for continuity.** Pass 1 of this
  entry proposed an outbound FTP/SFTP client adapter here under
  `Capability.STORAGE` (server half → `openframe-protocol`, client half
  → here). Pass 2 (`openframe-protocol` draft 7) moved both halves of
  FTP into `openframe-protocol-ftp` together, removing it as a
  candidate here entirely. **Pass 3 (`openframe-protocol` draft 8,
  current)** reverses pass 2: the boundary is now "by peer, not by
  protocol" — FTP's *server* half (accepting uploads from unknown
  callers) stays in `openframe-protocol-ftp`, but the *client* half
  (connecting to one specific named third-party FTP server) is a
  third-party-peer integration and belongs back here, in
  `openframe-adapters`, as originally thought. Its exact `Capability`
  fit is explicitly **not yet decided** (draft 8's own open decision
  D11 — `STORAGE` is a candidate, not settled) — don't treat the old
  pass-1 `STORAGE` placement as confirmed; it's a plausible answer to
  an open question, not a closed one. Same reopened status applies to
  RTMP push and RTSP pull (D11 again — none of the eleven existing
  `Capability` members fits either yet) and to a raw SMTP relay
  (tentatively `NOTIFICATION`, same not-yet-added caveat as below).
- **Full-text/structured search** — Elasticsearch, OpenSearch. Reuses
  `Capability.SEARCH` (already shared with vector/graph stores); own
  query shape (term/boolean queries, not vector similarity or Cypher).
- **Secrets management** (`BaseSecretsProvider` — also pre-named) —
  Vault, AWS/GCP/Azure secret managers. Not CRUD-shaped — versioned key
  lookups need their own port design, not a `BaseRepository` extension.
- **Feature flags** (`BaseFeatureFlagProvider` — also pre-named) —
  LaunchDarkly, Unleash, GrowthBook. Not CRUD-shaped — boolean/variant
  evaluation.
- **Distributed locking** — own Redis/etcd/Zookeeper client (never the
  `openframe-adapters-db-redis` package itself). `acquire`/`release`/
  `extend` is close to CRUD-shaped but isn't quite it.
- **Notifications** (email/SMS/push, plus Slack/webhook alerts and
  PagerDuty/Opsgenie-style paging) — SES, SendGrid, Twilio, FCM, Slack
  incoming webhooks, PagerDuty. Shaped like `BaseProducer`
  (fire-and-forget/ack), not `BaseRepository`. Intended new taxonomy
  member: `Capability.NOTIFICATION` — named now, not added to the enum
  yet (see below). The role this covers is distinct from this repo's
  existing logging/OTel-metrics signals: those are machine-consumed
  telemetry (dashboards, alerting pipelines that process metrics);
  `NOTIFICATION` covers reaching an actual human or external system
  directly (an email landing in an inbox, a page firing, a Slack
  message posting) — a different capability, not a backend for the
  telemetry this repo already has. Candidate justification, following
  the same bar `Capability.SEARCH` met (shared by multiple genuinely
  analogous backends, not invented for one): email, SMS, push, and
  chat/paging providers are all the same operational role — deliver a
  message to an end-human/device via an external provider — which is
  why this is a stronger fit than forcing it onto the existing `QUEUE`
  member (which specifically describes message *brokers* with
  consumer-side subscribe/ack semantics; SES/SendGrid/Slack have none
  of that).
  - **Do not add `Capability.NOTIFICATION` to the enum speculatively.**
    Per this repo's own closed-taxonomy discipline (ADR-006;
    `Capability.TRANSPORT` was not repurposed for inbound transport
    servers in the `openframe-protocol` design review for the same
    reason) — add the member only once a real adapter (email, SMS,
    push, or paging) is actually being built, not ahead of one. This
    bullet records the intended name and justification so that moment
    doesn't have to re-derive either from scratch.
- **Identity/auth verification** — Auth0, Okta, Keycloak token
  introspection or user lookup.
- **Rate limiting** — same Redis-driver-directly caveat as locking.

Deliberately out of scope for now: workflow orchestration (Temporal/
Camunda — too large a port surface for one method), schema registries
(Kafka-ecosystem-specific, niche), payment processing (too
domain-specific for generic infra adapters).

### openframe-suite

- `openframe-suite[rest]`, `[inference]`, `[worker]` topology bundles
- Six templates: `modal-template-fastapi` (exists), `modal-template-realtime`, `modal-template-event`, `modal-template-worker`, `modal-template-inference`, `modal-template-grpc`

---

## Changelog

## v3.3.0 — ApplicationBootstrap.compose()/get_all()/registry, port init timeouts (non-breaking)

> Resolves the "three application wiring options" ambiguity tracked above by consolidating to one recommended class (`ApplicationBootstrap`) at three levels of ceremony. See [Design Decisions](../architecture/design-decisions.md) and [How It Works § Choosing a Wiring Pattern](../../developer-guide/how-it-works.md#choosing-a-wiring-pattern).

- `ApplicationBootstrap.compose(*ports)` — new classmethod; zero-subclass entry point for a service with one or a few ports.
- `ApplicationBootstrap.get_all(capability)` — new method, mirrors `PluginRegistry.get_all()`.
- `ApplicationBootstrap.registry` — new read-only property exposing the underlying `PluginRegistry`.
- `PluginRegistry(default_init_timeout=...)` / `register(..., init_timeout=...)` (mirrored on `ApplicationBootstrap`) — bound how long `initialize_all()` waits for a port's `initialize()`. Both default to `None` (no timeout) — fully backward-compatible.
- Fixed: `TracingProxy`'s `asyncio.iscoroutinefunction` deprecation; `AmbiguousCapabilityError` now mirrors `capability`/`matches` into `context`.
- Full changelog: [`.github/CHANGELOG.md`](https://github.com/Furious-Meteors/openframe-core/blob/production/.github/CHANGELOG.md#v330--2026-09-28).

---

## v3.1.0 — contracts/ Merged into ports/, outbound/ Sub-module Introduced (breaking)

> Ecosystem packages pinned `openframe-core>=3.0,<4`; `openframe-adapters` has migrated its imports to `openframe.core.ports`.

- `openframe.core.contracts` renamed to `openframe.core.ports`. All names previously importable from `openframe.core.contracts` are now importable from `openframe.core.ports`. No compatibility shim — update all imports.
- `openframe.core.ports` now exports both the port primitives (`BasePort`, `Capability`, `Identity`, `Lifecycle`, `PluginStatus`, `PluginHealth`, `PluginContext`, `PrincipalContext`, `TenantContext`) and the outbound protocols (`BaseRepository`, `BaseProducer`, `BaseConsumer`) from a single unified module.
- `BaseRepository`, `BaseProducer`, `BaseConsumer` moved into a new `openframe/core/ports/outbound/` sub-module, mirroring `openframe/core/inbound/` on the driving side of the hexagon. The public API is unchanged — `from openframe.core.ports import BaseRepository` still works; the explicit sub-module path is now `from openframe.core.ports.outbound import BaseRepository`. Future capability-specific outbound protocols (`BaseSecretsProvider`, `BaseObjectStore`, `BaseFeatureFlagProvider` from `openframe-infra`) will be added to `ports/outbound/`.

---

## v3.0.0 — Unified Port + Lifecycle Contract (breaking)

> Migration guide: [ADR-006](../architecture/adrs/adr-006-unified-port-lifecycle.md). Ecosystem packages pinned `openframe-core>=3.0,<4`; all packages have since migrated.

**Removed:**

- `openframe.core.health` — `HealthCheck` Protocol (`ping()`/`is_ready()`) deleted. Health is now `Lifecycle.health() -> PluginHealth` in `openframe.core.ports`.
- `openframe.core.plugins.contracts` / `OpenFramePlugin` — deleted. A plugin is now just a registered `BasePort`. No separate plugin protocol exists.
- `openframe.core.errors` — the `PluginError` family moved into `openframe.core.exceptions` under the new `OpenFrameError` root. No deprecated aliases.
- Pre-v3 lifecycle-free ports — `BaseRepository`, `BaseProducer`, `BaseConsumer` no longer exist as bare domain-method-only Protocols; rebuilt on `BasePort`.

**Added:**

- `openframe.core.contracts` *(merged into `openframe.core.ports` in v3.1.0 — see below)* — apex module: `Identity`, `Lifecycle`, `BasePort` (`@runtime_checkable`), `Capability` (closed `str` enum), `PluginStatus`, `PluginHealth`, `PluginContext`, `PrincipalContext`, `TenantContext`.
- `openframe.core.inbound` — driving side of the hexagon: `UseCase[TIn, TOut]`, `CommandHandler[TIn]`, `QueryHandler[TIn, TOut]`, `RequestContext`.
- `openframe.core.exceptions.OpenFrameError` — single root for all ecosystem exceptions. `ErrorCode` and `Severity` `StrEnum`s. `AdapterError` and `PluginError` families re-parented under it.
- `openframe.core.telemetry.record_error()` — structured error→span recording seam. Called at `TracingProxy`, `TelemetryMiddleware`, and `PluginRegistry` boundary seams.
- `openframe.core.plugins.PluginRegistry` — now keys on `Capability` enum; `get()` is strict (`AmbiguousCapabilityError` on >1 match).
- `openframe.core.runtime.ApplicationBootstrap` — optional async context-manager composition root.
- `openframe.core.testing` — `InMemoryRepository`, `FakeProducer`, `FakeConsumer` (all `BasePort`-satisfying); `PortContractTests`, `LifecycleContractTests`, `RepositoryContractTests`, `ProducerContractTests`, `ConsumerContractTests`.

**Changed:**

- `BaseRepository[T]`, `BaseProducer[T]`, `BaseConsumer[T]` — now extend `BasePort`. Every port has `name`/`version`/`capability`/`initialize`/`shutdown`/`health`.
- Version bumped `2.0.0` → `3.0.0` in `pyproject.toml`.
- 284 tests. All run in under 1 second.

---

## v2.0.0 — Namespace & Settings Stabilisation (breaking)

- `openframe.core.config` — `BaseAdapterSettings` stabilised as the base for all adapter settings.
- `openframe.core.exceptions` — `AdapterError` `__str__` format locked to `[adapter.operation] message`.
- Namespace package (`pkgutil.extend_path`) stabilised. Ecosystem packages begin using the `openframe.*` namespace.

---

## 2026-06-13 — v1.0.0 Initial Release

- `openframe.core.exceptions` — `AdapterError` base class and five typed subclasses. `__str__` produces `[adapter.operation] message` rather than a raw tuple repr. `super().__init__(message)` passes only the message to `Exception.__init__`.
- `openframe.core.config` — `BaseAdapterSettings` Pydantic `BaseSettings` subclass with four common fields: `adapter_name`, `connection_timeout` (30 s), `operation_timeout` (10 s), `max_retries` (3).
- `openframe.core.ports` — `BaseRepository[T]`, `BaseProducer[T]`, `BaseConsumer[T]` as `runtime_checkable` Protocols. `BaseConsumer` uses a push-based handler model (`Callable[[T], Awaitable[None]]`).
- `openframe.core.health` — `HealthCheck` Protocol with `ping()` and `is_ready()` *(removed in v3.0.0)*.
- `openframe.core.telemetry` — `setup_telemetry()`, `get_tracer()`, `get_meter()`, `record_lifecycle_event()`. Removes `_grafana_headers()` — authentication handled natively via `OTEL_EXPORTER_OTLP_HEADERS`. Replaces `MODAL_ENV` with `OPENFRAME_ENV`.
- `openframe.core.tracing` — `TracingProxy` with fixed method caching. Original template captured `method` at first access (stale snapshot). This implementation resolves fresh inside `_traced` on every invocation — safe for reconnecting adapters.
- `openframe.core.middleware` — `TelemetryMiddleware` as pure ASGI middleware (not Starlette `BaseHTTPMiddleware`). Duration metric uses unit `"s"` per OTel HTTP semantic conventions. Five metric instruments. `x-session-id` injection. Does not call `setup_telemetry()`.
- `openframe.core.middleware.types` — `ASGIScope`, `ASGIMessage`, `Receive`, `Send`, `ASGIApp` stdlib-only type aliases.
- 112 tests across 8 modules. `conftest.py` resets OTel `Once._done` guards between tests — without this, `set_tracer_provider()` silently fails from test 2 onwards.
- Published to PyPI as `openframe-core==1.0.0`.
