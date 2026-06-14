# First Code Change

The smallest meaningful change to `openframe-core`: adding a new exception subclass.

---

## Add `AdapterSerializationError`

A new exception for when a message cannot be serialised before publishing to a queue.

**1. Add the class to `openframe/core/exceptions/errors.py`:**

```python
class AdapterSerializationError(AdapterError):
    """
    Raised when a message cannot be serialised for transport.

    Typical causes: non-JSON-serialisable payload, missing required field
    on the message schema, codec version mismatch.

    Raise with cause chaining::

        raise AdapterSerializationError(
            "Payload contains non-serialisable type datetime",
            adapter="kafka",
            operation="publish",
            cause=exc,
        ) from exc
    """
```

**2. Export it from `openframe/core/exceptions/__init__.py`:**

```python
from openframe.core.exceptions.errors import (
    ...
    AdapterSerializationError,
)

__all__ = [
    ...
    "AdapterSerializationError",
]
```

**3. Add a test in `tests/test_exceptions.py`:**

```python
def test_serialization_error_instantiates() -> None:
    exc = AdapterSerializationError("payload not serialisable", "kafka", "publish")
    assert isinstance(exc, AdapterError)
    assert "kafka" in str(exc)
    assert "publish" in str(exc)
```

**4. Run the tests:**

```bash
pytest tests/test_exceptions.py -v
```

**5. Bump the version in `pyproject.toml`:**

```toml
version = "1.0.1"
```

This is a backwards-compatible addition — a minor bump is correct. No existing code breaks.

---

## What Not to Change

- Never modify `AdapterError.__init__` — all five subclasses inherit from it and changing the signature is a breaking change.
- Never add infrastructure imports to any `openframe/core/` module.
- Never change `BaseRepository`, `BaseProducer`, or `BaseConsumer` method signatures — these are the stable contract that every adapter in the ecosystem implements.
