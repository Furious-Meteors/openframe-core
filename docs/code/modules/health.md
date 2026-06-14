# health

`openframe/core/health/protocol.py` · Health check port for all OpenFrame adapter packages.

---

## Classes

### `HealthCheck`

```python
@runtime_checkable
class HealthCheck(Protocol):
    async def ping(self) -> bool: ...
    async def is_ready(self) -> bool: ...
```

Health check port. Every adapter implements `ping()` and `is_ready()`.

#### `ping()`

Low-cost liveness check. Verify the adapter can reach its backend. Should complete within milliseconds — a TCP connect attempt or `SELECT 1` is appropriate. Called frequently by load balancers and watchdog processes.

**Returns:** `bool` — `True` if the backend is reachable, `False` otherwise. Must not raise — return `False` on any failure.

#### `is_ready()`

Full readiness check. Verify the adapter is fully ready to serve requests — schema correct, migrations applied, connection pool has healthy connections. More expensive than `ping()`. Called once at application startup.

**Returns:** `bool` — `True` if the adapter is ready to serve, `False` otherwise. Must not raise — return `False` on any failure.

---

## Example Implementation

```python
class PostgresRepository:
    async def ping(self) -> bool:
        try:
            await self._pool.fetchval("SELECT 1")
            return True
        except Exception:
            return False

    async def is_ready(self) -> bool:
        try:
            count = await self._pool.fetchval(
                "SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public'"
            )
            return count > 0
        except Exception:
            return False

assert isinstance(PostgresRepository(), HealthCheck)  # True
```
