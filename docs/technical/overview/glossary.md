# Glossary

Terms used throughout the OpenFrame documentation. Each term is defined precisely — where a term has a common informal usage that differs from its meaning here, the difference is noted.

---

## A

**Adapter** — a concrete implementation of a port. An adapter knows about a specific driver (asyncpg, motor, aiokafka) and translates between the driver's API and the port's protocol. Adapters live in `openframe-adapters-*` packages, never in `openframe-core`.

**AdapterError** — the base exception class for all OpenFrame adapter packages. All five subclasses (`AdapterConnectionError`, `AdapterQueryError`, `AdapterNotFoundError`, `AdapterConfigurationError`, `AdapterTimeoutError`) extend it. Services catch `AdapterError` as a single catch point.

**ASGI** — Asynchronous Server Gateway Interface. The standard Python interface for async web servers and applications. `openframe-core` middleware targets ASGI directly, not any specific framework.

## B

**BaseAdapterSettings** — the Pydantic `BaseSettings` subclass that every adapter's settings class inherits from. Reads fields from environment variables at instantiation time.

**BaseConsumer[T]** — the generic `runtime_checkable` Protocol for message queue consumer adapters. Methods: `subscribe`, `ack`, `nack`, `close`.

**BaseProducer[T]** — the generic `runtime_checkable` Protocol for message queue producer adapters. Methods: `publish`, `publish_batch`, `close`.

**BaseRepository[T]** — the generic `runtime_checkable` Protocol for persistence adapters. Methods: `get`, `list`, `create`, `update`, `delete`.

## D

**Dependency order** — the rule inside `openframe-core` that modules may only import from modules lower in the DAG: `exceptions` → `config` → `ports` → `health` → `telemetry` → `tracing` → `middleware`. Circular imports are a build failure.

## H

**HealthCheck** — a `runtime_checkable` Protocol with two methods: `ping()` (cheap liveness) and `is_ready()` (full readiness). Every adapter implements both.

**Hexagonal architecture** — the architectural pattern enforced across all OpenFrame templates. Business logic lives in `core/` and has no knowledge of infrastructure. Adapters translate between `core/` ports and external systems. The pattern is also called Ports and Adapters.

## L

**Lifecycle event** — a named counter increment recorded via `record_lifecycle_event(event_name)`. `"cold_start"` is the most common value, called from Modal template `@enter` hooks.

## M

**Meta-package** — a published Python package with no code, only dependency declarations. `openframe-adapters` is a meta-package whose optional extras (`[postgres]`, `[redis]`, `[all]`) pull in individual adapter packages.

**Modal** — the serverless GPU/CPU platform used as the reference deployment target for all OpenFrame templates. `openframe-core` has zero Modal imports — Modal knowledge lives in `modal_app.py` only.

## N

**Namespace package** — a Python package using `pkgutil.extend_path` in `__init__.py` to allow multiple installed packages to contribute modules to the same top-level import path. `openframe/` is a namespace package, allowing `openframe-core`, `openframe-adapters`, and all other family packages to coexist under `openframe.*`.

## O

**OPENFRAME_ENV** — the platform-agnostic environment tag (`dev`, `feat`, `prod`). Replaces `MODAL_ENV` from the production template. Modal users set it in `configure_env_vars()`.

**OTel** — OpenTelemetry. The observability framework used for distributed tracing and metrics. `openframe-core` depends on `opentelemetry-api` and `opentelemetry-sdk`.

**OTLP** — OpenTelemetry Protocol. The wire format used to export traces and metrics to a backend (Grafana Cloud, Honeycomb, Datadog, etc.). Configured via `OTEL_EXPORTER_OTLP_ENDPOINT` and `OTEL_EXPORTER_OTLP_HEADERS`.

## P

**Port** — an abstract interface defined as a Python `Protocol` in `openframe-core`. Ports define *what* the contract is; adapters define *how* it is fulfilled for a specific backend.

**Protocol** — a Python structural subtyping mechanism (`typing.Protocol`). A class satisfies a Protocol if it has matching method signatures — no inheritance required. All ports in `openframe-core` are `runtime_checkable` Protocols.

## R

**runtime_checkable** — a decorator applied to all port Protocols. Enables `isinstance(obj, BaseRepository)` checks at runtime. Note: `isinstance(obj, BaseRepository[str])` raises `TypeError` — only the unparameterised form is supported at runtime.

## T

**TracingProxy** — the zero-code async telemetry sidecar in `openframe.core.tracing`. Wraps any object and creates an OTel child span for every async method call. The `deps.py` wiring layer in templates applies `TracingProxy` after creating the real adapter.

**TelemetryMiddleware** — the pure ASGI middleware in `openframe.core.middleware`. Records one OTel span and five HTTP metric instruments per request. Does not call `setup_telemetry()` — that is an application startup concern.
