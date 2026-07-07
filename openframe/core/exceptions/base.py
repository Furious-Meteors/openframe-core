"""
openframe/core/exceptions/base.py
====================================
``OpenFrameError`` — the single root of every exception raised anywhere in
the OpenFrame ecosystem.

Every error family (``AdapterError``, ``PluginError``, and every downstream
package's family) derives from ``OpenFrameError``, so a single
``except OpenFrameError`` is a catch point for the whole platform::

    try:
        await service.do_work()          # Postgres, Kafka, an AI provider...
    except OpenFrameError as err:        # catches AdapterError, PluginError, ...
        log.warning("openframe failure", code=err.code, retryable=err.retryable)

Bottom of the dependency DAG
----------------------------
This module imports only ``openframe.core.exceptions.codes`` and the stdlib.
It never imports from any higher layer (config, contracts, telemetry, ...).
Observability integration is done the other way round: the telemetry layer
imports ``OpenFrameError`` and reads its plain data — the error never reaches
up. See ``openframe.core.telemetry.record_error``.

Semantics as data
-----------------
``severity`` and ``retryable`` are carried as fields (not encoded only in the
subclass) so retry logic, gateways, and middleware can act on them without an
``isinstance`` ladder over every concrete error class.

Enrichment on the way up
------------------------
``correlation_id`` and ``context`` are mutable — an upper-layer seam
(``TracingProxy``, ``TelemetryMiddleware``) stamps the current trace id onto
the error as it bubbles up. The error never fetches it.

Dependency order: imports ``openframe.core.exceptions.codes`` only.

.. stability: stable
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from openframe.core.exceptions.codes import ErrorCode, Severity

__all__ = ["OpenFrameError"]

__stability__ = "stable"


class OpenFrameError(Exception):
    """
    Root exception for the entire OpenFrame ecosystem.

    Class-level ``code``/``severity``/``retryable`` act as defaults; a
    subclass sets them once as class attributes and every instance inherits
    them. They can still be overridden per-instance via the constructor.

    Attributes:
        code:           Namespaced ``domain.kind`` identity (serialisable).
        message:        Human-readable description of the failure.
        severity:       :class:`~openframe.core.exceptions.codes.Severity`.
        retryable:      Whether the operation is safe to retry.
        correlation_id: Trace/correlation id, stamped by an upper layer.
        context:        Structured, non-PII detail (mutable, enrichable).
        cause:          Underlying exception, if any. Chain at the raise site
                        with ``raise OpenFrameError(...) from exc``.
    """

    # Class-level defaults — subclasses override.
    code: str = ErrorCode.OPENFRAME
    severity: Severity = Severity.ERROR
    retryable: bool = False

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        severity: Severity | None = None,
        retryable: bool | None = None,
        correlation_id: str | None = None,
        context: Mapping[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        """
        Initialise the error.

        Args:
            message:        Human-readable description of the failure.
            code:           Override the class-level code for this instance.
            severity:       Override the class-level severity.
            retryable:      Override the class-level retryable flag.
            correlation_id: Trace/correlation id (usually stamped later).
            context:        Structured detail; copied into a mutable dict.
            cause:          Underlying exception, or None.
        """
        super().__init__(message)
        self.message = message
        self.code = str(code) if code is not None else str(type(self).code)
        self.severity = severity if severity is not None else type(self).severity
        self.retryable = retryable if retryable is not None else type(self).retryable
        self.correlation_id = correlation_id
        self.context: dict[str, Any] = dict(context) if context else {}
        self.cause = cause

    def __str__(self) -> str:
        """Return the message (subclasses may add structured prefixes)."""
        return self.message

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            f"message={self.message!r}, "
            f"code={self.code!r}, "
            f"severity={self.severity!r}, "
            f"retryable={self.retryable!r}, "
            f"cause={self.cause!r})"
        )
