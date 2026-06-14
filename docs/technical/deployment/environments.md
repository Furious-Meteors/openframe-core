# Environments

Three environments, each mapped to a git branch, each deployed to Modal automatically on push.

---

## Environment Matrix

| Environment | Branch | `OPENFRAME_ENV` | Purpose |
|---|---|---|---|
| `feat` | `feat/*` | `feat` | Feature development, short-lived |
| `dev` | `dev` | `dev` | Integration, shared team environment |
| `prod` | `production` | `prod` | Live traffic |

Modal users map `MODAL_ENV` to `OPENFRAME_ENV` in their `configure_env_vars()` helper. For non-Modal deployments, set `OPENFRAME_ENV` directly as an environment variable.

---

## Environment Variable Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENFRAME_ENV` | No | `dev` | Deployment environment tag attached to all OTel spans and metrics |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | No | — | OTLP base URL. When absent, no-op providers are used and nothing is exported |
| `OTEL_EXPORTER_OTLP_HEADERS` | No | — | Auth headers, e.g. `Authorization=Basic <token>` |
| `OTEL_SERVICE_NAME` | No | `openframe` | Service name tag on all telemetry |
| `OTEL_SERVICE_VERSION` | No | `1.0.0` | Service version tag on all telemetry |
| `OTEL_METRIC_EXPORT_INTERVAL_MS` | No | `15000` | Metric export interval in milliseconds |
