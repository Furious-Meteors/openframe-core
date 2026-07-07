# Modules

`openframe-core` v3.0.0 contains eleven modules, organised into three tiers: foundation, contract layer, and application modules. Each page documents every public class, method, and function with parameters, return types, and what it raises.

| Module | Import path | What it provides |
|---|---|---|
| [exceptions](exceptions.md) | `openframe.core.exceptions` | `OpenFrameError` (root) · `ErrorCode` · `Severity` · `AdapterError` (+5) · `PluginError` (+4, incl. `AmbiguousCapabilityError`) |
| [config](config.md) | `openframe.core.config` | `BaseAdapterSettings` |
| [contracts](contracts.md) | `openframe.core.contracts` | `Identity` · `Lifecycle` · `BasePort` · `Capability` · `PluginStatus` · `PluginHealth` · `PluginContext` · `PrincipalContext` · `TenantContext` |
| [ports](ports.md) | `openframe.core.ports` | `BaseRepository[T]` · `BaseProducer[T]` · `BaseConsumer[T]` — `BasePort` + domain methods |
| [inbound](inbound.md) | `openframe.core.inbound` | `UseCase[TIn, TOut]` · `CommandHandler[TIn]` · `QueryHandler[TIn, TOut]` · `RequestContext` |
| [telemetry](telemetry.md) | `openframe.core.telemetry` | `setup_telemetry` · `get_tracer` · `get_meter` · `record_lifecycle_event` · `record_error` |
| [tracing](tracing.md) | `openframe.core.tracing` | `TracingProxy` |
| [middleware](middleware.md) | `openframe.core.middleware` | `TelemetryMiddleware` · ASGI type aliases |
| [plugins](plugins.md) | `openframe.core.plugins` | `PluginRegistry` |
| [runtime](runtime.md) | `openframe.core.runtime` | `ApplicationBootstrap` |
| [testing](testing.md) | `openframe.core.testing` | `InMemoryRepository` · `FakeProducer` · `FakeConsumer` · contract test base classes |

!!! note "health module removed in v3.0.0"
    The `openframe.core.health` module and `HealthCheck` protocol were removed in v3.0.0. Health is now part of the unified `Lifecycle` contract in `openframe.core.contracts` (`Lifecycle.health() -> PluginHealth`). See the [contracts module](contracts.md) and [ADR-006](../../technical/architecture/adrs/adr-006-unified-port-lifecycle.md).
