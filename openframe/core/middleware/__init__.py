"""
openframe/core/middleware/
===========================
Pure ASGI telemetry middleware and shared ASGI type aliases for the
OpenFrame ecosystem.

The middleware is framework-agnostic — it works with FastAPI, Starlette,
Litestar, or any bare ASGI application.

Usage::

    from openframe.core.middleware import TelemetryMiddleware

    app = TelemetryMiddleware(app)

ASGI type aliases::

    from openframe.core.middleware import ASGIApp, ASGIScope, ASGIMessage, Receive, Send

    def my_middleware(app: ASGIApp) -> ASGIApp:
        async def wrapped(scope: ASGIScope, receive: Receive, send: Send) -> None:
            ...
        return wrapped

Note on ``isinstance`` with type aliases:
    ``ASGIScope = MutableMapping[str, Any]`` is a subscripted generic alias.
    ``isinstance({}, ASGIScope)`` raises ``TypeError`` — use the origin type::

        from collections.abc import MutableMapping
        isinstance({}, MutableMapping)  # ✓ works

    To inspect the alias::

        from typing import get_origin
        get_origin(ASGIScope) is MutableMapping  # ✓ True
"""
from __future__ import annotations

from openframe.core.middleware.telemetry import TelemetryMiddleware
from openframe.core.middleware.types import (
    ASGIApp,
    ASGIMessage,
    ASGIScope,
    Receive,
    Send,
)

__all__ = [
    "TelemetryMiddleware",
    "ASGIApp",
    "ASGIScope",
    "ASGIMessage",
    "Receive",
    "Send",
]
