# Design Decisions

Non-obvious architectural decisions made during the design and review process. Formal ADRs are in [Technical → Architecture → ADRs](adrs/adr-001-namespace.md). This page captures implementation-level decisions that do not warrant a full ADR.

---

## Exception Naming Prefix

**Chosen:** All exception subclasses carry the `Adapter` prefix: `AdapterConnectionError`, `AdapterTimeoutError`.

**Rejected:** `ConnectionError`, `TimeoutError` (mirrors stdlib names).

**Why:** `ConnectionError` and `TimeoutError` are Python built-ins since Python 3.3. Defining identically-named classes in a package and importing them with `from openframe.core.exceptions import *` would shadow the built-ins in any file that does so, producing confusing tracebacks where `except ConnectionError` catches the wrong class.

**Consequences:** Slightly more verbose class names. No risk of stdlib shadowing in any consuming code.

---

## super().__init__(message) Only

**Chosen:** `AdapterError.__init__` calls `super().__init__(message)` with only the message string. Other fields (`adapter`, `operation`, `cause`) are stored as named instance attributes.

**Rejected:** `super().__init__(message, adapter, operation, cause)` passing all four args to `Exception.__init__`.

**Why:** `Exception.__str__` returns `str(self.args[0])` when `len(self.args) == 1`, but returns `str(self.args)` (a tuple representation) when `len(self.args) > 1`. Passing all four args produces `str(exc) == "('entity not found', 'postgres', 'get', None)"` — a raw tuple, not a readable error message.

**Consequences:** `AdapterError` requires an explicit `__str__` override (implemented). `self.args` contains only `(message,)`.

---

## TracingProxy _cache as Closure Identity Cache

**Chosen:** `_cache` stores the `_traced` closure by method name to avoid repeated closure allocation. The closure itself resolves the method fresh on every invocation via `getattr(wrapped, name)`.

**Rejected (v1 original):** `object.__setattr__(self, name, _traced)` — permanently shadowed `__dict__` entries, breaking reconnecting adapters.

**Rejected (v2 attempt):** `_cache` storing the resolved `method` object — still a stale snapshot when the wrapped object replaces its method after reconnect.

**Why:** Reconnecting drivers (asyncpg pools, Redis clients) may replace their own internal method objects after a reconnect. A proxy that holds a reference to the original method object calls dead code. Resolving via `getattr` on every call ensures the proxy always delegates to whatever the wrapped object's current method is.

**Consequences:** `_cache` entries are closures (cheap allocations) rather than method references. The slight overhead of one `getattr` per async call is the correct trade-off for reconnect safety.

---

## Pure ASGI Middleware

**Chosen:** `TelemetryMiddleware` uses `async def __call__(self, scope, receive, send)` — raw ASGI.

**Rejected:** Starlette's `BaseHTTPMiddleware`.

**Why:** `BaseHTTPMiddleware` has documented limitations around streaming responses and request body access. It buffers responses, which prevents streaming use cases. Pure ASGI middleware receives the raw `send` callable and can intercept it with a thin wrapper (`send_with_telemetry`) that captures the status code without buffering.

**Consequences:** Route template extraction is less convenient — Starlette sets `scope["route"]` to a `Route` object only after routing completes; the raw path is used as a fallback. This increases metric cardinality for routes with path parameters but is the correct trade-off for framework independence.

---

## Three Application Wiring Options (unresolved, watch)

Three wiring patterns now coexist in `openframe-core`:

1. **`deps.py` + `lru_cache`** — module-level cached factory functions.
   Simple, familiar, no framework. Most existing templates use this.
2. **`PluginRegistry` direct** — explicit registry construction and
   `initialize_all()` call in a `lifespan` handler. Full control, no
   abstraction layer.
3. **`ApplicationBootstrap`** — subclass-based composition root. Manages
   the `PluginRegistry` internally and adds `configure()` → `start()` →
   `stop()` lifecycle.

The ambiguity is better than before — `ApplicationBootstrap` has a name,
a docstring, and the correct `stop()` behaviour (port shutdown +
`shutdown_telemetry()`). But it is still three options without a clear
hierarchy.

**The risk:** if the docs don't establish `ApplicationBootstrap` as the
recommended path — with the other two documented as deliberate
alternatives and the conditions under which you'd choose each — the
ambiguity just gets more documented rather than actually resolved. A new
adapter author reads the code and sees three equivalent-looking patterns
with no signal about which to start from.

**The resolution path:** update the developer guide and the runtime module
doc to name `ApplicationBootstrap` as the default starting point, and
explain the two alternatives as escape hatches:

- Use `PluginRegistry` directly when you need fine-grained control over
  initialization order or want to avoid the subclass pattern.
- Use `deps.py` + `lru_cache` when you're wiring a single port without a
  full startup/shutdown lifecycle (e.g. a simple stateless function).

This is tracked in the roadmap as a documentation task.

---

## contracts/ Five-Module Dependency Chain (structural watch)

`openframe.core.contracts` is currently five files with a clean linear
import chain:

```
capability → context → health → identity → lifecycle → port
```

Each module imports only from the one below it. The DAG is correct today.

**The concern:** five files for what is one concept — a registrable,
lifecycle-managed, identity-tagged port. The split is principled (each
module has one thing), but it creates a surface that is easy to expand
carelessly. A sixth module that is not as cleanly separated (for example,
one that imports from two non-adjacent layers, or one that blurs the
concept boundary) would make `contracts/` harder to reason about than the
original single-file approach, not easier.

**The boundary condition:** the current five-module structure is fine as
long as each module stays focused on a single, independently nameable
concept. The signal to watch for is a new module that:

- Imports from more than one existing `contracts/` module at the same
  level (rather than strictly from the layer below it), or
- Represents a concept that could have been a dataclass or a small
  addition to an existing module rather than its own file.

If either of those happens, consolidation should be considered before the
chain grows to six or seven files.

**Chosen:** OTLP authentication is handled via `OTEL_EXPORTER_OTLP_HEADERS` env var only. No vendor-specific header construction in `openframe-core`.

**Rejected:** `_grafana_headers()` function from the production template that constructs a `Basic` auth header from Grafana-specific credentials.

**Why:** The OTel SDK natively reads `OTEL_EXPORTER_OTLP_HEADERS` and applies it to every export request. Implementing Grafana-specific header construction in `openframe-core` couples the package to one specific backend, contradicting the platform-agnostic design. Any OTLP-compatible backend (Grafana Cloud, Honeycomb, Datadog, Jaeger, self-hosted Tempo) works by setting the standard env var.

**Consequences:** Grafana Cloud users set `OTEL_EXPORTER_OTLP_HEADERS="Authorization=Basic $(echo -n '<user>:<token>' | base64)"`. This is documented in the telemetry module docstring.
