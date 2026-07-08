# Modules

`openframe-core` v3.1.0 contains ten modules, organised into three tiers: foundation, contract layer, and application modules. Each page documents every public class, method, and function with parameters, return types, and what it raises.

| Module | Import path | What it provides |
|---|---|---|
| [exceptions](exceptions.md) | `openframe.core.exceptions` | `OpenFrameError` (root) · `ErrorCode` · `Severity` · `AdapterError` (+5) · `PluginError` (+4, incl. `AmbiguousCapabilityError`) |
| [config](config.md) | `openframe.core.config` | `BaseAdapterSettings` |
| [ports](ports.md) | `openframe.core.ports` | `Identity` · `Lifecycle` · `BasePort` · `Capability` · `PluginStatus` · `PluginHealth` · `PluginContext` · `PrincipalContext` · `TenantContext` · `BaseRepository[T]` · `BaseProducer[T]` · `BaseConsumer[T]` |
| [inbound](inbound.md) | `openframe.core.inbound` | `UseCase[TIn, TOut]` · `CommandHandler[TIn]` · `QueryHandler[TIn, TOut]` · `RequestContext` |
| [telemetry](telemetry.md) | `openframe.core.telemetry` | `setup_telemetry` · `get_tracer` · `get_meter` · `record_lifecycle_event` · `record_error` |
| [tracing](tracing.md) | `openframe.core.tracing` | `TracingProxy` |
| [middleware](middleware.md) | `openframe.core.middleware` | `TelemetryMiddleware` · ASGI type aliases |
| [plugins](plugins.md) | `openframe.core.plugins` | `PluginRegistry` |
| [runtime](runtime.md) | `openframe.core.runtime` | `ApplicationBootstrap` |
| [testing](testing.md) | `openframe.core.testing` | `InMemoryRepository` · `FakeProducer` · `FakeConsumer` · contract test base classes |

!!! note "health module removed in v3.0.0; contracts merged into ports in v3.1.0"
    The `openframe.core.health` module and `HealthCheck` protocol were removed in v3.0.0. Health is now part of the unified `Lifecycle` contract in `openframe.core.ports` (`Lifecycle.health() -> PluginHealth`). In v3.1.0, `openframe.core.contracts` was merged into `openframe.core.ports`, and the outbound protocols (`BaseRepository`, `BaseProducer`, `BaseConsumer`) moved into an internal `ports/outbound/` sub-module mirroring `openframe.core.inbound` on the driving side — the public import path (`from openframe.core.ports import ...`) is unaffected. No compatibility shim exists at the old `openframe.core.contracts` path. See the [ports module](ports.md) and [ADR-006](../../technical/architecture/adrs/adr-006-unified-port-lifecycle.md).
