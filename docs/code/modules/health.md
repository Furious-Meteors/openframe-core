# health — removed in v3.0.0

!!! warning "Module removed"
    The `openframe.core.health` module and `HealthCheck` protocol (`ping()`/`is_ready()`) were **removed in v3.0.0**. There is no replacement shim or deprecated alias.

Health is now part of the unified `Lifecycle` contract in `openframe.core.contracts`:

```python
from openframe.core.contracts import Lifecycle, PluginHealth, PluginStatus

# Instead of ping() / is_ready(), implement:
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

`Lifecycle.health()` absorbs both `ping()` (cheap liveness) and `is_ready()` (full readiness) into one call returning a rich `PluginHealth` snapshot. Liveness vs. readiness granularity is expressed in `PluginStatus` and `PluginHealth.details`, not in separate methods.

---

## Migration

| v2 | v3 |
|---|---|
| `from openframe.core.health import HealthCheck` | `from openframe.core.contracts import Lifecycle, PluginHealth, PluginStatus` |
| `async def ping(self) -> bool` | `async def health(self) -> PluginHealth` |
| `async def is_ready(self) -> bool` | `async def health(self) -> PluginHealth` |
| `isinstance(obj, HealthCheck)` | `isinstance(obj, Lifecycle)` |

---

## See Also

- [contracts module](contracts.md) — `Lifecycle`, `PluginHealth`, `PluginStatus`, `BasePort`
- [ADR-006](../../technical/architecture/adrs/adr-006-unified-port-lifecycle.md) — full rationale for the removal
