"""
openframe/core/exceptions/errors.py
=====================================
Structured exception hierarchy for all OpenFrame adapter packages.

Every adapter package raises only AdapterError subclasses — never raw
driver exceptions (psycopg errors, aioredis errors, aiokafka errors, etc.).
Services catch AdapterError at a single point regardless of which adapter
is wired in.

Raise with cause chaining at the raise site::

    try:
        result = await conn.execute(query)
    except SomeDriverError as exc:
        raise AdapterQueryError(
            message="Query failed",
            adapter="postgres",
            operation="get",
            cause=exc,
        ) from exc

Dependency order: this module has no imports from openframe.core.
"""
from __future__ import annotations

__all__ = [
    "AdapterError",
    "AdapterConnectionError",
    "AdapterQueryError",
    "AdapterNotFoundError",
    "AdapterConfigurationError",
    "AdapterTimeoutError",
]


class AdapterError(Exception):
    """
    Base exception for all OpenFrame adapter packages.

    All adapter packages raise only AdapterError subclasses — never raw
    driver exceptions. Services catch AdapterError for a single catch
    point regardless of which adapter is wired in.

    Attributes:
        message:   Human-readable description of what went wrong.
        adapter:   Adapter identifier, e.g. "postgres", "redis", "kafka".
        operation: Operation that failed, e.g. "get", "create", "publish".
        cause:     Underlying driver exception, if any. Always chain at
                   the raise site: ``raise AdapterXError(...) from exc``.

    The ``__str__`` format is::

        [adapter.operation] message
        [adapter.operation] message — caused by: <cause>
    """

    def __init__(
        self,
        message: str,
        adapter: str,
        operation: str,
        cause: Exception | None = None,
    ) -> None:
        """
        Initialise the exception.

        Args:
            message:   Human-readable description of the failure.
            adapter:   Adapter identifier (e.g. "postgres", "redis").
            operation: Operation that failed (e.g. "get", "create").
            cause:     Underlying driver exception, or None.
        """
        super().__init__(message)  # only message → self.args = (message,)
        self.message = message
        self.adapter = adapter
        self.operation = operation
        self.cause = cause

    def __str__(self) -> str:
        """
        Return a human-readable string including adapter, operation, and message.

        If a cause is present it is appended after \" — caused by: \".
        """
        base = f"[{self.adapter}.{self.operation}] {self.message}"
        if self.cause:
            return f"{base} — caused by: {self.cause}"
        return base

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            f"message={self.message!r}, "
            f"adapter={self.adapter!r}, "
            f"operation={self.operation!r}, "
            f"cause={self.cause!r})"
        )


class AdapterConnectionError(AdapterError):
    """
    Raised when the adapter cannot establish a connection to its backend.

    Typical causes: network unreachable, wrong host/port, TLS handshake
    failure, authentication rejected before a connection is established.

    Raise with cause chaining::

        raise AdapterConnectionError(
            "Cannot reach Postgres at localhost:5432",
            adapter="postgres",
            operation="connect",
            cause=original_exc,
        ) from original_exc
    """


class AdapterQueryError(AdapterError):
    """
    Raised when an operation fails after a connection is established.

    Typical causes: constraint violation, syntax error, permission denied
    on a specific table or topic, partial failure mid-batch.

    Raise with cause chaining::

        raise AdapterQueryError(
            "INSERT violated unique constraint on items.slug",
            adapter="postgres",
            operation="create",
            cause=original_exc,
        ) from original_exc
    """


class AdapterNotFoundError(AdapterError):
    """
    Raised when the requested entity does not exist in the backend.

    This is a semantic "not found" — the adapter successfully queried
    the backend but the entity is absent. Distinct from AdapterQueryError
    (which means the query itself failed).

    Raise without a cause when the backend returns a definitive empty
    result::

        raise AdapterNotFoundError(
            f"Item {item_id!r} not found",
            adapter="postgres",
            operation="get",
        )
    """


class AdapterConfigurationError(AdapterError):
    """
    Raised when required configuration is missing or invalid.

    Typical causes: required env var absent, value fails validation
    (wrong type, out of range), conflicting options.

    Raise at adapter initialisation time (not at first query) so
    misconfigured deployments fail fast on startup::

        raise AdapterConfigurationError(
            "DATABASE_URL must be set",
            adapter="postgres",
            operation="init",
        )
    """


class AdapterTimeoutError(AdapterError):
    """
    Raised when an operation exceeds its configured timeout.

    Distinct from AdapterConnectionError — the connection was established
    but the operation did not complete within the allowed window.

    Raise with cause chaining when wrapping an asyncio.TimeoutError::

        raise AdapterTimeoutError(
            "Query exceeded 10s operation_timeout",
            adapter="postgres",
            operation="get",
            cause=original_exc,
        ) from original_exc
    """
