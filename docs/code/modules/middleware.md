# middleware

`openframe/core/middleware/` · Pure ASGI telemetry middleware and type aliases.

---

## Overview

Two files: `telemetry.py` contains `TelemetryMiddleware`; `types.py` contains five ASGI type aliases shared across the OpenFrame ecosystem.

---

## Classes

### `TelemetryMiddleware`

`openframe/core/middleware/telemetry.py`

```python
class TelemetryMiddleware:
    def __init__(self, app: ASGIApp) -> None
    async def __call__(
        self,
        scope: ASGIScope,
        receive: Receive,
        send: Send,
    ) -> None
```

Pure ASGI telemetry middleware. Compatible with FastAPI, Starlette, Litestar, and bare ASGI. Records one OTel span and five HTTP metric instruments per request.

**Behaviour:**

- Only `scope["type"] == "http"` is instrumented. Lifespan and WebSocket scopes pass through without span or metrics.
- Does **not** call `setup_telemetry()`. Call `setup_telemetry()` once in the application `lifespan` handler.
- Instruments are created lazily on the first HTTP request.
- `x-session-id` is injected on every response that does not already carry one.

**Metric instruments:**

| Name | Type | Unit | Description |
|---|---|---|---|
| `http.server.request.count` | Counter | `1` | Total HTTP requests |
| `http.server.request.duration` | Histogram | `s` | Request duration in seconds |
| `http.server.active_requests` | UpDownCounter | `1` | In-flight requests |
| `http.server.error.count` | Counter | `1` | HTTP 4xx + 5xx responses |
| `http.server.response.size` | Histogram | `By` | Response body size |

**Span attributes:**

| Attribute | Source |
|---|---|
| `http.method` | `scope["method"]` |
| `http.target` | `scope["path"]` |
| `http.route` | `scope["route"].path` if Starlette/FastAPI, else `scope["path"]` |
| `http.scheme` | `scope["scheme"]` |
| `http.status_code` | captured from `http.response.start` message |
| `http.user_agent` | `user-agent` header |
| `net.host.name` | `scope["server"][0]` |
| `http.client_ip` | `x-forwarded-for` header or `scope["client"][0]` |
| `app.session_id` | `x-session-id` request header or generated UUID4 |

**Span status:** `StatusCode.ERROR` for HTTP ≥ 400, `StatusCode.OK` otherwise.

**Usage:**

```python
from openframe.core.middleware import TelemetryMiddleware

app = FastAPI(lifespan=lifespan)
app.add_middleware(TelemetryMiddleware)
```

---

## Type Aliases

`openframe/core/middleware/types.py`

Stdlib-only ASGI type aliases. No framework imports required.

```python
ASGIScope   = MutableMapping[str, Any]
ASGIMessage = MutableMapping[str, Any]
Receive     = Callable[[], Awaitable[ASGIMessage]]
Send        = Callable[[ASGIMessage], Awaitable[None]]
ASGIApp     = Callable[[ASGIScope, Receive, Send], Awaitable[None]]
```

All five are exported from `openframe.core.middleware` directly.

!!! note "Runtime isinstance"
    `isinstance({}, ASGIScope)` raises `TypeError` — subscripted generics do not support `isinstance`. Use `isinstance(obj, MutableMapping)` (the origin type) for runtime checks.
