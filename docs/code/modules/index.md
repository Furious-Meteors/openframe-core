# Modules

`openframe-core` contains seven modules. Each page documents every public class, method, and function with parameters, return types, and what it raises.

| Module | Import path | What it provides |
|---|---|---|
| [exceptions](exceptions.md) | `openframe.core.exceptions` | `AdapterError` + 5 typed subclasses |
| [config](config.md) | `openframe.core.config` | `BaseAdapterSettings` |
| [ports](ports.md) | `openframe.core.ports` | `BaseRepository[T]`, `BaseProducer[T]`, `BaseConsumer[T]` |
| [health](health.md) | `openframe.core.health` | `HealthCheck` |
| [telemetry](telemetry.md) | `openframe.core.telemetry` | `setup_telemetry`, `get_tracer`, `get_meter`, `record_lifecycle_event` |
| [tracing](tracing.md) | `openframe.core.tracing` | `TracingProxy` |
| [middleware](middleware.md) | `openframe.core.middleware` | `TelemetryMiddleware`, ASGI type aliases |
