"""
openframe/core/exceptions/adapter.py
======================================
Adapter (backend/infrastructure) exception family.

Every adapter package raises only ``AdapterError`` subclasses — never raw
driver exceptions (psycopg errors, aioredis errors, aiokafka errors, etc.).
Services catch ``AdapterError`` (or the ecosystem-wide ``OpenFrameError``)
at a single point regardless of which adapter is wired in.

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

All classes here derive from
:class:`~openframe.core.exceptions.base.OpenFrameError`, so every adapter
error is also catchable as ``OpenFrameError``. Each subclass sets its own
``domain.kind`` ``code`` and, where meaningful, a ``retryable`` default.

Dependency order: imports ``openframe.core.exceptions.base`` + ``.codes`` only.

.. stability: stable
"""
from __future__ import annotations

from openframe.core.exceptions.base import OpenFrameError
from openframe.core.exceptions.codes import ErrorCode

__all__ = [
    "AdapterError",
    "AdapterConnectionError",
    "AdapterQueryError",
    "AdapterNotFoundError",
    "AdapterConfigurationError",
    "AdapterTimeoutError",
]

__stability__ = "stable"


class AdapterError(OpenFrameError):
    """
    Base exception for all OpenFrame adapter packages.

    All adapter packages raise only ``AdapterError`` subclasses — never raw
    driver exceptions. Services catch ``AdapterError`` for a single catch
    point regardless of which adapter is wired in.

    Attributes:
        message:   Human-readable description of what went wrong.
        adapter:   Adapter identifier, e.g. "postgres", "redis", "kafka".
        operation: Operation that failed, e.g. "get", "create", "publish".
        cause:     Underlying driver exception, if any. Always chain at
                   the raise site: ``raise AdapterXError(...) from exc``.

    In addition to the inherited ``OpenFrameError`` fields (``code``,
    ``severity``, ``retryable``, ``correlation_id``, ``context``), the
    ``adapter`` and ``operation`` values are also recorded in ``context``.

    The ``__str__`` format is::

        [adapter.operation] message
        [adapter.operation] message — caused by: <cause>
    """

    code = ErrorCode.ADAPTER

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
        super().__init__(
            message,
            cause=cause,
            context={"adapter": adapter, "operation": operation},
        )
        self.adapter = adapter
        self.operation = operation

    def __str__(self) -> str:
        """
        Return a human-readable string including adapter, operation, and message.

        If a cause is present it is appended after " — caused by: ".
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

    Retryable — a transient connectivity failure is usually safe to retry.

    Raise with cause chaining::

        raise AdapterConnectionError(
            "Cannot reach Postgres at localhost:5432",
            adapter="postgres",
            operation="connect",
            cause=original_exc,
        ) from original_exc
    """

    code = ErrorCode.ADAPTER_CONNECTION
    retryable = True


class AdapterQueryError(AdapterError):
    """
    Raised when an operation fails after a connection is established.

    Typical causes: constraint violation, syntax error, permission denied
    on a specific table or topic, partial failure mid-batch.

    Not retryable by default — a failed query usually fails again identically.

    Raise with cause chaining::

        raise AdapterQueryError(
            "INSERT violated unique constraint on items.slug",
            adapter="postgres",
            operation="create",
            cause=original_exc,
        ) from original_exc
    """

    code = ErrorCode.ADAPTER_QUERY


class AdapterNotFoundError(AdapterError):
    """
    Raised when the requested entity does not exist in the backend.

    This is a semantic "not found" — the adapter successfully queried
    the backend but the entity is absent. Distinct from AdapterQueryError
    (which means the query itself failed).

    Not retryable — the entity's absence is a definitive result.

    Raise without a cause when the backend returns a definitive empty
    result::

        raise AdapterNotFoundError(
            f"Item {item_id!r} not found",
            adapter="postgres",
            operation="get",
        )
    """

    code = ErrorCode.ADAPTER_NOT_FOUND
    retryable = False


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

    code = ErrorCode.ADAPTER_CONFIGURATION


class AdapterTimeoutError(AdapterError):
    """
    Raised when an operation exceeds its configured timeout.

    Distinct from AdapterConnectionError — the connection was established
    but the operation did not complete within the allowed window.

    Retryable — a timeout is often transient (load spike, slow query).

    Raise with cause chaining when wrapping an asyncio.TimeoutError::

        raise AdapterTimeoutError(
            "Query exceeded 10s operation_timeout",
            adapter="postgres",
            operation="get",
            cause=original_exc,
        ) from original_exc
    """

    code = ErrorCode.ADAPTER_TIMEOUT
    retryable = True
