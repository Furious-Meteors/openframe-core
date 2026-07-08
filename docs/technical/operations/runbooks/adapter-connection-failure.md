# Adapter Connection Failure

An adapter raises `AdapterConnectionError` on every operation. The service is returning 500s.

---

## Symptoms

- All requests to routes that use a database adapter return HTTP 500
- Logs show `[postgres.connect] Cannot reach Postgres` or similar
- `port.health()` returns `PluginHealth(status=PluginStatus.UNAVAILABLE, ...)`
- OTel spans show `StatusCode.ERROR` on `repository.*.get` / `repository.*.create`

---

## Diagnosis

**1. Verify the backend is reachable.**

```bash
# From within the Modal container or local environment
python -c "
import asyncio, asyncpg
asyncio.run(asyncpg.connect(dsn='<DATABASE_URL>'))
print('connected')
"
```

**2. Check `health()` directly via `PluginRegistry`.**

```python
from openframe.core.ports import Capability
import asyncio

# If you have access to the registry instance:
port = registry.get(Capability.PERSISTENCE)
health = asyncio.run(port.health())
print(health.status)    # PluginStatus.READY / DEGRADED / UNAVAILABLE
print(health.message)   # error detail
```

**3. Verify env vars are present.**

```bash
modal app logs <app-name> | grep "DATABASE_URL\|POOL"
```

`AdapterConfigurationError` at startup (not `AdapterConnectionError`) means a required env var is missing — check `OPENFRAME_ENV`, `DATABASE_URL`, and any adapter-specific vars.

---

## Recovery

If the backend is down: restore the backend first. The adapter's connection pool will reconnect automatically when the backend returns.

If env vars are missing: update the Modal secret, redeploy:

```bash
modal secret update <secret-name> DATABASE_URL=<correct-value>
modal deploy modal_app.py
```

If a config change caused the breakage: roll back via git and redeploy:

```bash
git revert HEAD
git push origin production
```

---

## Prevention

Check `port.health()` in the `lifespan` handler and refuse startup if it returns `PluginStatus.UNAVAILABLE`. A service that cannot reach its database should not start serving traffic.

```python
from openframe.core.ports import Capability, PluginStatus

port = registry.get(Capability.PERSISTENCE)
health = await port.health()
if health.status == PluginStatus.UNAVAILABLE:
    raise RuntimeError(f"Port {port.name} unavailable at startup: {health.message}")
```
