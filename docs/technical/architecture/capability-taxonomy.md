# Capability Taxonomy

`openframe.core.ports.Capability` is a closed `str` `Enum` — the
typed vocabulary every `BasePort`'s `capability` attribute is drawn from,
and the type `PluginRegistry.get()`/`get_all()` key their lookups on
(ADR-006). This page is the human-readable reference derived from that
enum; when the two disagree, the enum in
[`openframe/core/ports/capability.py`](https://github.com/Furious-Meteors/openframe-core/blob/production/openframe/core/ports/capability.py)
is authoritative.

---

## Members

| Member | Value | Typical adapters |
|---|---|---|
| `PERSISTENCE` | `"persistence"` | SQL/NoSQL repositories (Postgres, Mongo, DynamoDB) |
| `CACHE` | `"cache"` | Ephemeral key-value stores (Redis, Memcached, in-process LRU) |
| `QUEUE` | `"queue"` | Async message production/consumption (Kafka, SQS, PubSub, Redis Streams) |
| `SECRETS` | `"secrets"` | Secret material retrieval (Vault, AWS Secrets Manager, env-based) |
| `FLAGS` | `"flags"` | Feature flag / toggle evaluation (LaunchDarkly, Unleash, config-based) |
| `STORAGE` | `"storage"` | Blob/object storage (S3, GCS, Azure Blob, local filesystem) |
| `TRANSPORT` | `"transport"` | Synchronous network transport (HTTP client, gRPC) |
| `INFERENCE` | `"inference"` | Model inference (LLM completion, classification, ranking) |
| `EMBEDDING` | `"embedding"` | Vector embedding generation |
| `SCHEDULE` | `"schedule"` | Deferred/recurring task scheduling (cron, Celery beat, cloud schedulers) |
| `SEARCH` | `"search"` | Full-text or vector search/retrieval (Elasticsearch, pgvector, Pinecone) |

---

## Usage

`Capability` subclasses `str`, so members compare equal to their value and
serialise cleanly to logs/JSON without an explicit `.value` access:

```python
from openframe.core.ports import Capability

assert Capability.PERSISTENCE == "persistence"
```

Every `BasePort` declares exactly one capability:

```python
class PostgresRepository:
    name = "postgres-main"
    version = "1.0.0"
    capability = Capability.PERSISTENCE
    # ... initialize / shutdown / health / get / list / create / update / delete ...
```

`PluginRegistry` lookups take a `Capability` member, not a raw string:

```python
repo = registry.get(Capability.PERSISTENCE)
```

`get()` is strict: it raises `AmbiguousCapabilityError` when more than one
port shares a capability. Use `get_all()` when multiple ports sharing a
capability is the intended configuration (e.g. a primary + replica
persistence pair):

```python
replicas = registry.get_all(Capability.PERSISTENCE)  # [primary, replica]
```

---

## Extending the taxonomy

Adding a new capability is a backward-compatible, additive change — a new
enum member in a minor version release. It is not something individual
adapter packages should do informally; propose new members against
`openframe-core` itself so the vocabulary stays closed and consistent
across the ecosystem. See
[ADR-006](adrs/adr-006-unified-port-lifecycle.md#alternatives-considered)
for why an open `str`/`NewType` taxonomy was rejected in favour of a
closed enum.

---

## Where capability-specific outbound port protocols live

Capability-specific outbound port protocols (`BaseRepository` for
`PERSISTENCE`, `BaseProducer`/`BaseConsumer` for `QUEUE`) live in
`openframe/core/ports/outbound/`, not in the adapter packages that
implement them. A new `Capability` member (e.g. `SECRETS`, `FLAGS`,
`STORAGE`) typically arrives together with a new base protocol in
`ports/outbound/` — `BaseSecretsProvider`, `BaseFeatureFlagProvider`,
`BaseObjectStore` — added to `openframe-core` by the package proposing
the capability (e.g. `openframe-infra`), not defined ad hoc inside that
package itself. Port *contracts* belong to `openframe-core`; only the
concrete *implementations* live downstream in `openframe-adapters` /
`openframe-infra`.
