"""
openframe/core/middleware/types.py
=====================================
ASGI type aliases shared across the OpenFrame ecosystem.

Import from ``openframe.core.middleware`` — not from this module directly.

These aliases provide proper typing for ASGI ``scope``, ``receive``, ``send``,
and ``app`` callables without importing from any framework (FastAPI, Starlette,
Litestar). Any package in the OpenFrame ecosystem that handles ASGI callables
should import these aliases rather than defining its own.

Runtime isinstance checks:
    ``isinstance({}, ASGIScope)`` — raises ``TypeError`` because
    ``MutableMapping[str, Any]`` is a subscripted generic alias and does not
    support ``isinstance``. Use the origin type for runtime checks::

        from collections.abc import MutableMapping
        isinstance({}, MutableMapping)  # ✓ works

    To inspect the alias type statically::

        from typing import get_origin
        get_origin(ASGIScope) is MutableMapping  # ✓ True

Dependency order: this module imports only from Python stdlib.
No openframe.core imports.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

__all__ = [
    "ASGIScope",
    "ASGIMessage",
    "Receive",
    "Send",
    "ASGIApp",
]

# Scope dict passed to every ASGI callable.
# Contains "type", "method", "path", "headers", etc.
ASGIScope = MutableMapping[str, Any]

# A single ASGI message dict (request body chunk, response start, etc.).
ASGIMessage = MutableMapping[str, Any]

# Callable that returns the next ASGI message from the client.
Receive = Callable[[], Awaitable[ASGIMessage]]

# Callable that sends an ASGI message to the client.
Send = Callable[[ASGIMessage], Awaitable[None]]

# A complete ASGI application or middleware.
ASGIApp = Callable[[ASGIScope, Receive, Send], Awaitable[None]]
