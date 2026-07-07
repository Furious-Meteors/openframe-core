# Glossary

Terms used throughout the OpenFrame documentation. Each term is defined precisely — where a term has a common informal usage that differs from its meaning here, the difference is noted.

---

## A

**Adapter** — a concrete implementation of a port. An adapter knows about a specific driver (asyncpg, motor, aiokafka) and translates between the driver's API and the port's protocol. Adapters live in `openframe-adapters-*` packages, never in `openframe-core`.

**AdapterError** — the base exception class for all adapter-related failures, derived from `OpenFrameError`. Five subclasses: `AdapterConnectionError`, `AdapterQueryError`, `AdapterNotFoundError`, `AdapterConfigurationError`, `AdapterTimeoutError`. See [error-taxonomy.md](../architecture/error-taxonomy.md).

**AmbiguousCapabilityError** — raised by `PluginRegistry.get()` when more than one registered port shares the requested `Capability`. Use `get_all()` when multiple ports sharing a capability is the intended configuration.

**ASGI** — Asynchronous Server Gateway Interface. The standard Python interface for async web servers and applications. `openframe-core` middleware targets ASGI directly, not any specific framework.

## B

**BaseAdapterSettings** — the Pydantic `BaseSettings` subclass that every adapter's settings class inherits from. Reads fields from environment variables at instantiation time.

**BaseConsumer[T]** — the generic `runtime_checkable` Protocol for message queue consumer adapters. Extends `BasePort`. Methods: `subscribe`, `ack`, `nack`, `close` plus identity/lifecycle from `BasePort`.

**BasePort** — the single unified base for every outbound port and every registrable plugin. Composes `Identity` (`name`/`version`/`capability`) and `Lifecycle` (`initialize`/`shutdown`/`health`). Defined in `openframe.core.contracts`.

**BaseProducer[T]** — the generic `runtime_checkable` Protocol for message queue producer adapters. Extends `BasePort`. Methods: `publish`, `publish_batch`, `close` plus identity/lifecycle from `BasePort`.

**BaseRepository[T]** — the generic `runtime_checkable` Protocol for persistence adapters. Extends `BasePort`. Methods: `get`, `list`, `create`, `update`, `delete` plus identity/lifecycle from `BasePort`.

## C

**Capability** — a closed `str` `Enum` (`PERSISTENCE`, `CACHE`, `QUEUE`, `SECRETS`, `FLAGS`, `STORAGE`, `TRANSPORT`, `INFERENCE`, `EMBEDDING`, `SCHEDULE`, `SEARCH`) that every `BasePort` declares as its `capability` attribute. `PluginRegistry.get()`/`get_all()` take a `Capability` member, not a raw string. See [capability-taxonomy.md](../architecture/capability-taxonomy.md).

**CommandHandler[TIn]** — a driving-side contract in `openframe.core.inbound` for CQRS-flavoured command handling. Has a single `execute(command, context)` method that returns `None`.

## D

**Dependency order** — the rule inside `openframe-core` that modules may only import from modules lower in the DAG: `exceptions` → `config` → `contracts` → `ports` / `inbound` / `telemetry` → `tracing` → `middleware` → `plugins` → `runtime`. Circular imports are a build failure. There is no standalone `health` node — health is part of `contracts` (`Lifecycle.health()`).

## E

**ErrorCode** — a `StrEnum` in `openframe.core.exceptions` enumerating the `domain.kind` codes owned by `openframe-core` (e.g. `adapter.connection`, `plugin.initialization`). Downstream packages declare their own codes without extending `ErrorCode`.

## H

**Hexagonal architecture** — the architectural pattern enforced across all OpenFrame templates. Business logic lives in `core/` and has no knowledge of infrastructure. Adapters translate between `core/` ports and external systems. Also called Ports and Adapters.

## I

**Identity** — a `Protocol` in `openframe.core.contracts` with three attributes: `name: str`, `version: str`, `capability: Capability`. Composes with `Lifecycle` to form `BasePort`.

**Inbound** — the driving side of the hexagon, modelled in `openframe.core.inbound`. `UseCase`, `CommandHandler`, and `QueryHandler` are invoked by inbound adapters (HTTP routes, message handlers, CLI) with a `RequestContext`.

## L

**Lifecycle** — a `Protocol` in `openframe.core.contracts` with three methods: `async initialize(context: PluginContext) -> None`, `async shutdown() -> None`, `async health() -> PluginHealth`. Health is exclusively `Lifecycle.health()` — there is no separate `HealthCheck` protocol.

**Lifecycle event** — a named counter increment recorded via `record_lifecycle_event(event_name)`. `"cold_start"` is the most common value, called from Modal template `@enter` hooks.

## M

**Meta-package** — a published Python package with no code, only dependency declarations. `openframe-adapters` is a meta-package whose optional extras (`[postgres]`, `[redis]`, `[all]`) pull in individual adapter packages.

**Modal** — the serverless GPU/CPU platform used as the reference deployment target for all OpenFrame templates. `openframe-core` has zero Modal imports — Modal knowledge lives in `modal_app.py` only.

## N

**Namespace package** — a Python package using `pkgutil.extend_path` in `__init__.py` to allow multiple installed packages to contribute modules to the same top-level import path. `openframe/` is a namespace package, allowing `openframe-core`, `openframe-adapters`, and all other family packages to coexist under `openframe.*`.

## O

**OPENFRAME_ENV** — the platform-agnostic environment tag (`dev`, `feat`, `prod`). Replaces `MODAL_ENV` from the production template. Modal users set it in `configure_env_vars()`.

**OpenFrameError** — the single root exception for all errors raised by the OpenFrame ecosystem. Carries `code`, `message`, `severity`, `retryable`, `correlation_id`, `context`, and `cause` as structured data. Both `AdapterError` and `PluginError` derive from it. See [error-taxonomy.md](../architecture/error-taxonomy.md).

**OTel** — OpenTelemetry. The observability framework used for distributed tracing and metrics. `openframe-core` depends on `opentelemetry-api` and `opentelemetry-sdk`.

**OTLP** — OpenTelemetry Protocol. The wire format used to export traces and metrics to a backend (Grafana Cloud, Honeycomb, Datadog, etc.). Configured via `OTEL_EXPORTER_OTLP_ENDPOINT` and `OTEL_EXPORTER_OTLP_HEADERS`.

## P

**Plugin** — in v3, a "plugin" is simply a registered `BasePort`. There is no separate plugin protocol. Any `BasePort` (i.e. any `BaseRepository`, `BaseProducer`, or `BaseConsumer`) can be registered in `PluginRegistry` without additional wrapper code.

**PluginHealth** — a dataclass in `openframe.core.contracts` returned by `Lifecycle.health()`. Carries `status: PluginStatus`, `message: str | None`, and `details: dict[str, Any]`.

**PluginRegistry** — the managed registry in `openframe.core.plugins`. Accepts any `BasePort`, initialises in registration order, shuts down in LIFO order, and looks up by `Capability` enum member. `get()` is strict — raises `AmbiguousCapabilityError` on >1 match.

**PluginStatus** — an enum in `openframe.core.contracts` with values `READY`, `DEGRADED`, `UNAVAILABLE`.

**Port** — an abstract interface defined as a Python `Protocol` in `openframe-core`. Ports define *what* the contract is; adapters define *how* it is fulfilled for a specific backend. Every port in v3 is a `BasePort` — identity-aware and lifecycle-aware.

**Protocol** — a Python structural subtyping mechanism (`typing.Protocol`). A class satisfies a Protocol if it has matching method signatures — no inheritance required. All ports in `openframe-core` are `runtime_checkable` Protocols.

## Q

**QueryHandler[TIn, TOut]** — a driving-side contract in `openframe.core.inbound` for CQRS-flavoured query handling. Has a single `execute(query, context) -> TOut` method.

## R

**record_error** — a function in `openframe.core.telemetry` that records a structured `OpenFrameError` on the active OTel span: sets `error.code`/`error.severity`/`error.retryable` attributes, records the exception event, stamps `correlation_id` back on the error, and increments the `openframe.error.count` metric exactly once per error object. Called automatically at `TracingProxy`, `TelemetryMiddleware`, and `PluginRegistry` boundary seams.

**RequestContext** — a frozen dataclass in `openframe.core.inbound` carrying a `correlation_id` and optional `PrincipalContext`/`TenantContext`. Constructed by inbound adapters and passed into `UseCase.execute()`.

**runtime_checkable** — a decorator applied to all port Protocols. Enables `isinstance(obj, BaseRepository)` checks at runtime. Note: `isinstance(obj, BaseRepository[str])` raises `TypeError` — only the unparameterised form is supported at runtime.

## S

**Severity** — a `StrEnum` in `openframe.core.exceptions` with values `WARNING`, `ERROR`, `CRITICAL`. Carried as data on every `OpenFrameError`.

## T

**TelemetryMiddleware** — the pure ASGI middleware in `openframe.core.middleware`. Records one OTel span and five HTTP metric instruments per request. Does not call `setup_telemetry()` — that is an application startup concern.

**TracingProxy** — the zero-code async telemetry sidecar in `openframe.core.tracing`. Wraps any object and creates an OTel child span for every async method call. The `deps.py` wiring layer in templates applies `TracingProxy` after creating the real adapter.

## U

**UseCase[TIn, TOut]** — the general driving-side contract in `openframe.core.inbound`. A structural `Protocol` with a single `execute(input, context) -> TOut` method. HTTP routes, message handlers, and CLI commands construct a `RequestContext` and call into a `UseCase` implementation.
