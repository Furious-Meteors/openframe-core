# Networking

`openframe-core` itself makes no network calls. The telemetry module exports to an OTLP endpoint when configured.

---

## OTLP Export

| Connection | Protocol | Auth |
|---|---|---|
| `OTEL_EXPORTER_OTLP_ENDPOINT/v1/traces` | HTTPS | `OTEL_EXPORTER_OTLP_HEADERS` |
| `OTEL_EXPORTER_OTLP_ENDPOINT/v1/metrics` | HTTPS | `OTEL_EXPORTER_OTLP_HEADERS` |

When `OTEL_EXPORTER_OTLP_ENDPOINT` is absent, no-op providers are installed and no network calls are made.

---

## Adapter Networking

Adapter packages (`openframe-adapters-*`) manage their own connections. `openframe-core` provides the `Lifecycle` contract in `contracts/` — specifically `Lifecycle.health() -> PluginHealth` — that adapters implement for connection verification. `PluginRegistry` calls `health()` during and after `initialize_all()`. `openframe-core` does not own any connection lifecycle itself.
