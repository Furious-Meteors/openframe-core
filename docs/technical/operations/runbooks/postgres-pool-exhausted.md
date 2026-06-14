# Postgres Pool Exhausted

All connections in the asyncpg pool are in use. New requests wait for a connection and time out with `AdapterTimeoutError`.

---

## Symptoms

- HTTP requests to database-backed routes time out (> `connection_timeout` seconds)
- `AdapterTimeoutError` in logs with `operation="get"` or `operation="create"`
- OTel spans show long duration on `repository.*.get` child spans
- `is_ready()` may return `False` if pool health check cannot acquire a connection

---

## Diagnosis

**1. Check pool size vs concurrent load.**

Pool size is set via `POOL_SIZE` env var (default: 10 in `PostgresSettings`). If concurrent requests exceed pool size, waiters queue up.

**2. Check for leaked connections.**

A connection is leaked when an adapter method raises an exception inside a transaction without rolling back and releasing. Look for spans with status `ERROR` that correspond to long-held connections.

**3. Check `operation_timeout`.**

`BaseAdapterSettings.operation_timeout` defaults to 10 seconds. If queries regularly take longer than this, the timeout fires before the query completes — increase the timeout or optimise the query.

---

## Recovery

**Immediate:** Increase pool size via env var and redeploy:

```bash
modal secret update openframe-postgres POOL_SIZE=20
modal deploy modal_app.py
```

**If connections are leaked:** Restart the container to force-close all connections:

```bash
modal app stop <app-name>
modal deploy modal_app.py
```

---

## Prevention

Use `async with pool.acquire() as conn:` (context manager) in all adapter methods. The context manager releases the connection on exit even if an exception is raised, preventing leaks.
