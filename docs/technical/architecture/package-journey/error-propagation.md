# Error Propagation

Every adapter in the OpenFrame ecosystem raises only `AdapterError` subclasses — never raw driver exceptions. This page shows how an error travels from the database driver to the HTTP response.

---

## Error Flow

```mermaid
sequenceDiagram
    participant DB as asyncpg
    participant AD as PostgresRepository
    participant TP as TracingProxy
    participant SVC as Service layer
    participant API as FastAPI route
    participant MW as TelemetryMiddleware

    DB-->>AD: asyncpg.PostgresError
    AD-->>AD: raise AdapterQueryError(\n  message="...",\n  adapter="postgres",\n  operation="get",\n  cause=exc\n) from exc
    AD-->>TP: AdapterQueryError propagates
    TP-->>TP: span closes (error recorded automatically)
    TP-->>SVC: AdapterQueryError propagates
    SVC-->>API: catches AdapterNotFoundError → 404\nor catches AdapterError → 500
    API-->>MW: response via send_with_telemetry
    MW-->>MW: status >= 400 → StatusCode.ERROR\nerror_count.add(1)
    MW-->>MW: emit WARNING log
```

---

## Exception Hierarchy

```
AdapterError (base)
├── AdapterConnectionError   — backend unreachable
├── AdapterQueryError        — operation failed post-connection
├── AdapterNotFoundError     — entity does not exist
├── AdapterConfigurationError— missing / invalid config
└── AdapterTimeoutError      — operation exceeded timeout
```

Service layers catch at the appropriate specificity:

```python
try:
    entity = await repo.get(entity_id)
except AdapterNotFoundError:
    raise HTTPException(status_code=404, detail="not found")
except AdapterError:
    raise HTTPException(status_code=500, detail="internal error")
```

---

## str() Format

`AdapterError.__str__` produces a structured string — not a raw tuple repr:

```
[postgres.get] entity not found
[postgres.create] insert failed — caused by: null constraint violation
```

The format is `[adapter.operation] message` with an optional `— caused by: <cause>` suffix when a cause is present.

→ See [exceptions module](../../../code/modules/exceptions.md) for the full class reference.
