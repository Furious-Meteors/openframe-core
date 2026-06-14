# Operations

Monitoring and runbooks for `openframe-core` in production. This section is for engineers responding to incidents or verifying system health.

---

## Runbooks

| Scenario | Runbook |
|---|---|
| Adapter cannot connect to backend | [Adapter Connection Failure](runbooks/adapter-connection-failure.md) |
| Queue consumer stops processing messages | [Queue Consumer Stuck](runbooks/queue-consumer-stuck.md) |
| OTel spans and metrics not appearing in backend | [Telemetry Export Failing](runbooks/telemetry-export-failing.md) |
| Postgres connection pool exhausted | [Postgres Pool Exhausted](runbooks/postgres-pool-exhausted.md) |
| Redis connection lost mid-operation | [Redis Connection Lost](runbooks/redis-connection-lost.md) |
| Modal cold starts spiking | [Modal Cold Start Spike](runbooks/modal-cold-start-spike.md) |

---

## Recovery Tools Available

| Tool | Effect |
|---|---|
| `adapter.ping()` | Low-cost connectivity check |
| `adapter.is_ready()` | Full readiness verification |
| `modal app logs <app-name>` | Stream live logs |
| `modal app stop <app-name>` | Stop environment |
| `record_lifecycle_event("recovery", {...})` | Record recovery event in metrics |
