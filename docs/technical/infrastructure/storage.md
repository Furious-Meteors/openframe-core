# Storage

`openframe-core` uses no persistent storage. It is a stateless library.

---

## Adapter Storage

Persistent storage concerns belong to adapter packages:

- `openframe-adapters-db-postgres` — relational, asyncpg
- `openframe-adapters-db-redis` — key-value, pub/sub
- `openframe-adapters-db-mongo` — document store

See the [openframe-adapters documentation](https://github.com/Furious-Meteors/openframe-adapters) when available.
