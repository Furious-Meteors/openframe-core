# Queue Consumer Stuck

A queue consumer (`BaseConsumer` implementation) has stopped processing messages. The queue is building up; no messages are being acknowledged.

---

## Symptoms

- Queue depth increasing with no drain
- No `ack()` calls visible in OTel spans
- Consumer container is running but `subscribe()` loop has stalled
- `port.health()` returns `PluginStatus.READY` (broker is reachable) but messages are not processed

---

## Diagnosis

**1. Check if the handler is hanging.**

```bash
modal app logs <app-name> | grep "consumer\|subscribe\|ack\|nack"
```

Look for the last message that was started but never acknowledged. A handler that raises an unhandled exception without triggering `nack()` will stall the consumer.

**2. Check broker connectivity.**

```python
from openframe.core.ports import PluginStatus
import asyncio

health = asyncio.run(consumer.health())
print(health.status)   # PluginStatus.READY = broker reachable; UNAVAILABLE = connection lost
```

If `health.status == PluginStatus.UNAVAILABLE`, this is a [Redis Connection Lost](redis-connection-lost.md) or broker outage, not a stuck consumer.

---

## Recovery

**If the handler is hanging on a specific message:**

Stop the consumer, drain or skip the problem message at the broker level, restart.

```bash
modal app stop <app-name>
# Skip / dead-letter the stuck message via broker admin UI or CLI
modal deploy modal_app.py
```

**If the consumer loop crashed silently:**

```bash
modal app stop <app-name>
modal deploy modal_app.py
```

Modal will cold-start a new container. `record_lifecycle_event("cold_start")` will fire and be visible in metrics.

---

## Prevention

Wrap all handler logic in `try/except AdapterError` and call `nack()` explicitly on failure. Never let an exception propagate out of the handler without an explicit `ack()` or `nack()` call.
