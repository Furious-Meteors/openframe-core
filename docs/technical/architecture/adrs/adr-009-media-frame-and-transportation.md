# ADR-009 — `MediaFrame`/`MediaKind` and `Transportation`

**Status:** Accepted — v3.9.0
**Relates to:** [ADR-006 — Unified Port + Lifecycle Contract](adr-006-unified-port-lifecycle.md) (intake-rule
precedent), [ADR-008 — `SessionHandler`](adr-008-session-handler.md) (most recent precedent for a focused
new concept module with no `BasePort`/`Capability` involvement).

---

## Context

Two unrelated, small, additive needs landed in the same release:

1. **A shared media-frame vocabulary.** `openframe-protocol-media` (RTMP ingest, HLS/DASH delivery) is
   about to be built, carrying high-density binary audio/video packets. A future, separate
   `openframe-adapters-media-ffmpeg` package will need to consume the same frame shape that
   `openframe-protocol-media` produces. If the frame type lived in `openframe-protocol-media` itself, the
   adapters package would have to depend on the protocol package just to share a data shape — or the
   dependency would have to run the other way, which is equally wrong, since neither family is naturally
   downstream of the other. Putting the shared type in `openframe-core`, which both families already
   depend on, avoids forcing either inverted or circular dependency.

2. **A `Transportation` enum**, proposed in an old `openframe-protocol` design spec years before any
   transport shipped, but never built. Six transports (HTTP, gRPC, SSE, WebSocket, webhooks, QUIC) have
   since shipped as concrete packages with no such enum. The user decided to build it now anyway,
   backfilling all six shipped transports as members, ahead of `openframe-protocol-media` adding two more
   (RTMP as a transport layer, alongside HLS/DASH).

These are independent decisions bundled into one ADR because they shipped in the same release and share
a theme: both are pure, additive vocabulary with zero behavioral consumers yet.

## Decision

### `MediaKind` / `MediaFrame` — `openframe.core.media`

Added as a new, focused concept module with no `BasePort`/`Capability` involvement — following the same
precedent `openframe.core.remote` set in v3.7.0 and `openframe.core.inbound.SessionHandler` reaffirmed in
ADR-008: a plain data/protocol shape shared between parties that already know each other by direct
construction doesn't need registry-lookup machinery.

This is the same reasoning ADR-006 used when it gave `ports/outbound/` a stated intake rule — "any future
capability-specific outbound port protocol belongs in `ports/outbound/`, ... not defined inside the
downstream package that first needs it" — generalized to a non-port concept: a shape two *sibling*
downstream families both need belongs in the shared ancestor (`openframe-core`), not in whichever sibling
happens to be built first. `MediaFrame` isn't a port, so it doesn't literally fall under ADR-006's intake
rule, but the underlying principle — cross-family sharing must live upstream of both families, or one of
them ends up depending on the other for no architectural reason — is exactly analogous.

Key field decisions:

- **`payload: bytes`, not `memoryview`.** A producer (e.g. pyrtmp) typically hands back a payload sliced
  out of a buffer it owns and may reuse for the next packet read off the socket. A `MediaFrame` is
  expected to outlive the callback that created it — it typically sits in a queue until a consumer drains
  it — so a `memoryview` into a buffer the producer later overwrites is a use-after-free class of bug: the
  frame's data would silently change after construction. `bytes` is an owned copy, so a frame means what
  it meant at construction time for as long as it exists.
- **`codec: str | None`, not a closed enum.** Codecs proliferate (h264, hevc, av1, aac, opus, and more to
  come) and a closed enum living in `openframe-core` would demand a core release every time a new codec
  needs support. This directly mirrors this repo's own existing precedent for error codes
  (`openframe.core.exceptions.codes.ErrorCode`): that module's docstring explains the taxonomy is typed
  `str` specifically so the vocabulary can grow per-package without a central registry every package must
  edit — "downstream packages do not extend this enum — they declare their own plain `'<domain>.<kind>'`
  strings." The same reasoning is cited directly and applied to `codec`.
- **`is_config` is kept separate from `is_keyframe`, and is the stronger invariant.** Dropping a keyframe
  leaves a stream corrupt until the next keyframe; dropping a config frame (e.g. an
  AVCDecoderConfigurationRecord) can make the entire stream undecodable with no recovery short of a new
  session. Any future consumer that sheds frames under backpressure must never drop a frame where
  `is_config=True`, under any shedding policy — this is recorded in the field's docstring as a standing
  invariant for future code to honor, not something enforced by this ADR's changes themselves.
- **`timestamp_ms`** carries the source-clock timestamp, for duration-based budgeting and audio/video
  sync, distinct from:
- **`received_at_ns`** (`time.perf_counter_ns()` at arrival) — the only way a consumer can measure
  queue dwell time, since `timestamp_ms` has no fixed relationship to local wall-clock time.
- **`track: str = "default"`** anticipates multi-bitrate/multi-audio-track support without building it —
  reserving the field now costs nothing and avoids a breaking field addition later.
- **No separate `size`/`length` field.** `len(payload)` is the canonical byte-budget unit; a redundant
  field could drift from the real payload.
- **`MediaKind`** stays a genuinely closed three-member enum (`VIDEO`/`AUDIO`/`METADATA`) — unlike codecs,
  these are structural categories of a media session, not something that grows per-codec. `METADATA` is
  reserved, undocumented-as-built, for a future gap/discontinuity marker; nothing in this release uses it.

### `Transportation` — `openframe.core.ports.transportation`

Added as a closed `str` `Enum`, built identically in shape to `Capability`
(`openframe/core/ports/capability.py`): same `class X(str, Enum)` base, same `__str__` returning
`.value`, same "Members:" docstring convention, same stdlib-only dependency footer. Ten members: the six
already-shipped transports (`HTTP`, `GRPC`, `SSE`, `WEBSOCKET`, `WEBHOOK`, `QUIC`) plus four media-adjacent
ones anticipated by `openframe-protocol-media` and friends (`RTMP`, `RTSP`, `HLS`, `DASH`). `RTSP` is
flagged in its own docstring line as "reserved — no server implementation ships yet," since no Python RTSP
server library exists and none is being built soon — the member exists for taxonomy completeness, not to
imply working support.

**Why now, despite six transports having shipped without it:** nothing in those six transports' delivery
*forced* `Transportation` to exist — each shipped as a self-contained package with no need to be named
alongside its siblings in one place. That changes as the transport family grows (RTMP/HLS/DASH joining
HTTP/gRPC/SSE/WebSocket/webhooks/QUIC) and cross-transport comparison becomes more likely to matter. Adding
the enum now is purely additive: zero existing consumers reference it, and nothing in the current codebase
breaks by its existence.

**`Capability.TRANSPORT`'s removal is deliberately deferred.** The original design doc that first proposed
`Transportation` bundled it with removing `Capability.TRANSPORT`, on the theory that `Transportation` would
supersede it. That removal is explicitly **out of scope** for this ADR and this release:
`Capability.TRANSPORT` is untouched — not deprecated, not referenced from `Transportation`, not scheduled
for removal in a specific future version. Removing a member from a closed enum like `Capability` is a
breaking change for anyone matching on it exhaustively, and would require a future major version bump under
this project's own semantic-versioning discipline (see ADR-006's precedent for treating enum-shape changes
as version-significant). This release is purely additive.

## Consequences

- **New module `openframe.core.media`** (`openframe/core/media/__init__.py`,
  `openframe/core/media/frame.py`) exports `MediaKind`, `MediaFrame`. Marked
  `.. stability: experimental`, same convention as `openframe.core.remote`.
- **New module `openframe.core.ports.transportation`** exports `Transportation`, re-exported from
  `openframe.core.ports.__init__` alongside `Capability` under "Port primitives."
- **No change to any existing contract.** `Capability` (including `Capability.TRANSPORT`) is untouched.
- **Version bump: `3.8.0` → `3.9.0`** — additive, non-breaking minor version.

## Alternatives considered

- **Define `MediaFrame` inside `openframe-protocol-media` itself.** Rejected: a future
  `openframe-adapters-media-ffmpeg` package would then have to depend on `openframe-protocol-media` purely
  to share a data shape, an inverted dependency relative to how adapters/protocol families are organized
  elsewhere in this ecosystem.
- **Make `MediaFrame.codec` a closed enum.** Rejected for the same reason `ErrorCode` stays a `str`
  taxonomy at the edges: codecs proliferate faster than core releases should need to track them.
- **Remove `Capability.TRANSPORT` in this same release, as the old design doc proposed.** Rejected —
  deferred to a future major version; see "Decision" above.
- **Build `Transportation` incrementally, one member per transport package, instead of backfilling all
  ten at once.** Rejected: the enum has no consumers yet regardless of how it's populated, and
  backfilling the six already-shipped transports now avoids a future PR whose only content is "add the
  transports that already existed."
