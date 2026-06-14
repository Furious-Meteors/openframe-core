# config

`openframe/core/config/settings.py` · Base settings class for all OpenFrame adapter packages.

---

## Overview

Every adapter's settings class inherits from `BaseAdapterSettings` and declares its own fields. Pydantic reads field values from environment variables automatically — field name maps to env var name (case-insensitive). Missing required fields raise `pydantic_core.ValidationError` at instantiation time.

---

## Classes

### `BaseAdapterSettings`

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class BaseAdapterSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )
    adapter_name: str = "openframe"
    connection_timeout: float = 30.0
    operation_timeout: float = 10.0
    max_retries: int = 3
```

**Fields:**

| Field | Type | Default | Env var | Description |
|---|---|---|---|---|
| `adapter_name` | `str` | `"openframe"` | `ADAPTER_NAME` | Identifies the adapter in logs and traces |
| `connection_timeout` | `float` | `30.0` | `CONNECTION_TIMEOUT` | Seconds to wait when establishing a connection |
| `operation_timeout` | `float` | `10.0` | `OPERATION_TIMEOUT` | Seconds to wait for a single operation |
| `max_retries` | `int` | `3` | `MAX_RETRIES` | Maximum retry attempts on transient failure |

**Usage:**

```python
from openframe.core.config import BaseAdapterSettings

class PostgresSettings(BaseAdapterSettings):
    database_url: str          # reads DATABASE_URL — required
    pool_size: int = 10        # reads POOL_SIZE — optional, default 10

# Raises pydantic_core.ValidationError immediately if DATABASE_URL is missing
settings = PostgresSettings()
print(settings.database_url)   # "postgresql://user:pass@host/db"
print(settings.pool_size)      # 10 or value of POOL_SIZE env var
```

**Raises:**

| Exception | Condition |
|---|---|
| `pydantic_core.ValidationError` | Required field has no env var set, or env var value cannot be coerced to the field's type |
