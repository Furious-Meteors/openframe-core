# ADR-008 — `SessionHandler`: a driving-side contract for long-lived connections

**Status:** Accepted — v3.8.0
**Extends:** [ADR-006 — Unified Port + Lifecycle Contract](adr-006-unified-port-lifecycle.md)'s
`openframe.core.inbound` module (`UseCase`, `CommandHandler`, `QueryHandler`, `RequestContext`).

---

## Context

`openframe-protocol` builds two request/response transports (`-http`, `-grpc`) on
`openframe.core.inbound`'s existing contracts: one input in, one output out, done. Neither shape
fits a long-lived connection — WebSocket (bidirectional) or Server-Sent Events (unidirectional,
server→client) — where a handler may receive zero or many inbound events and send zero or many
outbound events over the connection's lifetime.

`openframe-protocol`'s own design spec sketches a `SessionHandler[TEvent]` contract
(`on_open`/`on_event`/`on_close`) as the intended fix, with an explicit rule: incubate it in
`openframe-protocol-base` first, and only promote it to `openframe-core` once three independent
session transports have proven the shape against the same conformance suite — the same
rule-of-three discipline this repo already applies to `Capability` and `ErrorCategory` additions.

That sketch has zero lines of code anywhere, in either repo, and the design spec itself flags one
concrete unresolved question as a blocker: **how does a handler actually send events to the
client?** `on_open`/`on_event`/`on_close` describe the inbound (driving) half of the contract only
— receiving events and lifecycle notifications — but say nothing about the outbound half.

## Decision

**Build `SessionHandler` directly in `openframe.core.inbound`, not incubated in
`openframe-protocol-base` first** — a deliberate deviation from the stated rule-of-three gate (see
"Why skip incubation" below) — alongside a new `Session[TOut]` contract that resolves the
unanswered outbound-events question.

- **`Session[TOut]`** (`openframe/core/inbound/session.py`) — `@runtime_checkable Protocol`,
  carries `context: RequestContext` (built once per session, not once per event — a session has
  one correlation id for its whole lifetime) plus two methods:
  - `async def send(self, event: TOut) -> None` — push one outbound event.
  - `async def close(self, reason: CloseReason = CloseReason.COMPLETED) -> None` — end the
    session. Idempotent.

  **Push-based, not a pull-based `AsyncIterator[TOut]` return value.** A handler can call
  `session.send()` from inside `on_event` (responding to an inbound message) *or* from a
  background task it spawns at `on_open` (e.g. forwarding events from an unrelated source — a
  Kafka consumer — into an already-open connection). A generator return value can't express the
  latter without the handler building its own internal queue anyway, at which point that queue
  *is* a `Session` object in a different shape — so `Session` names the thing directly instead of
  leaving every handler to reinvent it.

- **`SessionHandler[TIn, TOut]`** (same module) — `@runtime_checkable Protocol` with three methods:
  - `async def on_open(self, session: Session[TOut]) -> None` — accept (return normally) or reject
    (raise) a new session. A raised exception flows through
    `openframe.protocol.base.errors.categorize`/`build_envelope` — the exact same mapping path
    every other inbound contract's failures already use — rather than a second return-value
    channel a caller would need a separate check for.
  - `async def on_event(self, session: Session[TOut], event: TIn) -> None` — called once per
    inbound event, in arrival order. **Never called at all** for a one-directional transport (SSE,
    which has no client→server events) — a valid, expected lifecycle, not a contract violation.
  - `async def on_close(self, session: Session[TOut], reason: CloseReason) -> None` — called
    exactly once, however the session ended.

- **`CloseReason`** (same module) — closed `Enum`: `COMPLETED`, `CLIENT_DISCONNECT`,
  `SERVER_SHUTDOWN`, `ERROR`. Every session transport maps its own disconnect/shutdown signal onto
  one of these four, mirroring how `ErrorCategory` gives every transport one shared vocabulary for
  errors instead of each inventing its own.

- **Testing**: `SessionHandlerContractTests` (`testing/contracts/inbound.py`, alongside the
  existing three inbound contract-test classes) and `InMemorySession`
  (`testing/fakes/inbound.py`, alongside `EchoUseCase`/`SpyCommandHandler`/`SpyQueryHandler`) —
  same fixture-based subclass pattern, same zero-pytest-at-module-level discipline.

### Why skip incubation in `-base`

The rule-of-three gate exists to de-risk a contract shape against real, demonstrated need before
it lands in the platform kernel. The one genuine open question that gate would have surfaced —
how outbound events are sent — is resolved by this decision itself (the `Session` push model
above), reasoned from first principles against both a one-directional transport (SSE) and a
bidirectional one (WebSocket) rather than discovered incrementally across three separate builds.
Incubating a second time in `-base` before any transport exists to prove it against would add a
layer of indirection with no remaining uncertainty left to burn down. This is recorded here as an
explicit, conscious exception — not a precedent for skipping the rule-of-three discipline
generally; `Capability`/`ErrorCategory`-style additions should still default to it.

## Consequences

- **`openframe.core.inbound.__init__`** exports `SessionHandler`, `Session`, `CloseReason`
  alongside the existing `UseCase`, `CommandHandler`, `QueryHandler`, `RequestContext`.
- **No change to any existing contract.** `UseCase`/`CommandHandler`/`QueryHandler`/
  `RequestContext` are untouched — this is a pure addition.
- **`openframe-protocol-base` gains transport-neutral session plumbing next** (a `run_session`
  loop helper and a `SessionConformanceTests` suite), reusing `build_request_context` and
  `categorize`/`build_envelope` as-is — both already generic enough for a session's single
  per-connection context and in-band error events, confirmed during design research, not assumed.
- **SSE is the first transport to implement `SessionHandler`**, as a new module inside
  `openframe-protocol-http` (per that repo's own design spec placement decision) rather than a new
  package — chosen because it is one-directional (`on_event` never fires), the lower-risk half of
  the contract to prove first. WebSocket (bidirectional, its own package-boundary question) is
  explicitly out of scope for this ADR.
- **Version bump: `3.7.0` → `3.8.0`** — additive, non-breaking minor version.

## Alternatives considered

- **Pull-based `AsyncIterator[TOut]` return value from `on_open`.** Rejected: maps cleanly onto
  SSE alone, but can't express a handler pushing an event from outside its own generator's loop
  (an external task, or `on_event` triggering an unprompted send) without the handler building an
  internal queue regardless — see "Decision" above.
- **Model session rejection as a return value** (e.g. `on_open` returns `bool`) instead of raising.
  Rejected: every other inbound contract in this module signals failure by raising, and a second,
  bespoke "did it accept" channel here would mean `SessionHandler` is the only inbound contract a
  caller can't route through the shared `categorize`/`build_envelope` error path uniformly.
- **Incubate in `openframe-protocol-base` first, per the design spec's own stated rule.**
  Rejected for this specific contract — see "Why skip incubation" above. Not a general reversal of
  the rule-of-three discipline for future additions.
