# Secrets & Config

`openframe-core` has no secrets of its own. This page documents how templates using `openframe-core` manage secrets and configuration.

---

## Modal Secret Pattern

Templates store secrets as Modal Secrets and inject them as environment variables:

```python
# modal_app.py
@app.function(
    secrets=[
        modal.Secret.from_name("openframe-otel"),     # OTLP endpoint + headers
        modal.Secret.from_name("openframe-postgres"),  # DATABASE_URL
    ]
)
async def handler(): ...
```

---

## Config Reading Pattern

`BaseAdapterSettings` reads all config from environment variables at instantiation. No config file parsing. No `os.environ.get()` scattered through business logic.

```python
class PostgresSettings(BaseAdapterSettings):
    database_url: str         # reads DATABASE_URL — required
    pool_size: int = 10       # reads POOL_SIZE — optional, default 10

# Instantiation raises pydantic_core.ValidationError immediately if DATABASE_URL is missing
settings = PostgresSettings()
```
