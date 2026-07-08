# Health

Health is part of the unified `Lifecycle` contract in `openframe.core.ports`. Every `BasePort` implements a single `health()` method that returns a rich `PluginHealth` snapshot — there is no separate health protocol.

```python
from openframe.core.ports import Lifecycle, PluginHealth, PluginStatus

async def health(self) -> PluginHealth:
    try:
        await self._pool.fetchval("SELECT 1")
        return PluginHealth(status=PluginStatus.READY)
    except Exception as exc:
        return PluginHealth(
            status=PluginStatus.UNAVAILABLE,
            message=str(exc),
        )
```

`Lifecycle.health()` is the single canonical health primitive. Liveness vs. readiness granularity — or any other reporting distinction an adapter needs — is expressed through `PluginStatus` and `PluginHealth.details`, not through separate methods:

```python
# Minimal
PluginHealth(status=PluginStatus.READY)

# With detail
PluginHealth(
    status=PluginStatus.READY,
    details={"ping_ms": 2.1, "schema_ok": True},
)

# Degraded
PluginHealth(
    status=PluginStatus.DEGRADED,
    message="replica lag 5s",
    details={"lag_s": 5},
)
```

`PluginRegistry` calls `health()` on every registered port to build a live snapshot — see [`PluginRegistry.health_all()`](plugins.md).

---

## See Also

- [ports module](ports.md) — `Lifecycle`, `PluginHealth`, `PluginStatus`, `BasePort`
- [ADR-006](../../technical/architecture/adrs/adr-006-unified-port-lifecycle.md) — full design rationale
