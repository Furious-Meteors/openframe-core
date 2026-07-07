# Redis Connection Lost

The Redis adapter loses its connection mid-operation. Subsequent operations raise `AdapterConnectionError`.

---

## Symptoms

- Operations that use Redis (caching, pub/sub, queue backing) start raising `AdapterConnectionError`
- `port.health()` returns `PluginHealth(status=PluginStatus.UNAVAILABLE, ...)`
- OTel spans show `AdapterConnectionError` on `cache.*` or `queue.*` child spans

---

## Diagnosis

**1. Verify Redis is reachable.**

```bash
redis-cli -u <REDIS_URL> ping
# → PONG if reachable
```

**2. Check if the connection was lost due to a timeout.**

Redis servers close idle connections after `timeout` seconds (default: 0 = never, but managed Redis services often set this to 300s). If the adapter holds a single connection and doesn't reconnect, it fails after the server closes the idle connection.

---

## Recovery

`redis-py` with `auto_reconnect=True` (the default) reconnects automatically on the next operation. If the adapter is not reconnecting:

- Verify the adapter uses `redis.asyncio.Redis` with `retry_on_timeout=True`
- `TracingProxy` is safe for reconnects — it resolves the method fresh on every call, so the new connection's methods are called correctly after reconnect

**If Redis itself is down:** restore Redis first. The adapter will reconnect automatically when Redis returns.

---

## Prevention

Use connection pooling (`ConnectionPool`) rather than a single connection. Pool connections are acquired per operation and returned immediately, eliminating idle timeout issues.
