# ADR-003 — Per-Adapter Async Strategy

**Status:** Accepted — v1.0.0

---

**Chosen:** Async strategy is decided per adapter based on native driver support. Drivers that are async-native (asyncpg, motor, redis-py, aiokafka, nats-py, qdrant-client) stay async. Blocking drivers (pymilvus, cassandra-driver, faiss-cpu) are wrapped in `asyncio.get_event_loop().run_in_executor(None, ...)` inside the adapter.

**Rejected:** Forcing all adapters async via executor wrappers regardless of driver support. Forcing all adapters sync with `run_in_executor` at the service layer.

**Why:** Forcing async-native drivers through executor wrappers adds unnecessary thread-pool overhead and loses the cooperative scheduling benefits of native coroutines. Forcing every driver through the same pattern introduces artificial complexity in adapters whose drivers already handle async correctly.

The `run_in_executor` wrapper for blocking drivers is the correct escape hatch — it moves the blocking call off the event loop thread without requiring the driver to be rewritten.

**Consequences:** Adapter packages must document their async strategy in their own `README.md` and module docstrings. The `BaseRepository` Protocol uses `async def` for all methods — sync adapters expose an async interface that wraps sync calls internally. Concurrent load on `run_in_executor` adapters (pymilvus, FalkorDB) can create thread-pool contention; this must be explicitly designed for in those adapters.
