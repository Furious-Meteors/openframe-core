# ADR-010 — `MediaSegment`

**Status:** Accepted — v3.10.0
**Relates to:** [ADR-009 — `MediaFrame`/`MediaKind` and `Transportation`](adr-009-media-frame-and-transportation.md)
(establishes the pattern this ADR repeats and the module `MediaSegment` joins)

---

## Context

`openframe-protocol-media`'s next capability is pulling/polling HLS and DASH streams: fetching whole
segment files (fMP4/CMAF `.m4s` or MPEG-TS `.ts`) rather than the already-classified, already-demuxed
elementary-stream units `MediaFrame` represents. A real segment file is a muxed container holding both
audio and video together — nothing in `openframe.core.media` currently represents "one fetched segment
before demuxing," and the same cross-family sharing need ADR-009 already established for `MediaFrame`
applies here unchanged: a future `openframe-adapters-media-ffmpeg` package will need to consume the same
segment shape `openframe-protocol-media`'s puller produces, and neither family should depend on the other
to share it.

This is not a new architectural decision — it's the ADR-009 pattern repeating for a second, related type.
See ADR-009 for the full cross-family sharing rationale (the intake-rule analogy to ADR-006, the
"no `BasePort`/`Capability` involvement" reasoning); it is not re-derived here.

Two real spikes against actual `ffmpeg`-produced HLS and DASH streams shaped this type's fields:

1. **Sequence numbering and dedup.** HLS's `media_sequence` (the `m3u8` library assigns this per-segment
   automatically) and DASH's resolved segment number (from `SegmentTemplate`/`SegmentTimeline`, hand-resolved
   and verified byte-for-byte against 80 real segments with zero mismatches) are both reliable, absolute,
   monotonically increasing identifiers. Segment URIs are not: a spike confirmed URIs can repeat across an
   unrelated stream/encoder restart, because segment filename counters reset. Dedup-by-URI would silently
   treat two genuinely different segments as the same one.
2. **Discontinuity and wall-clock timing are both origin-dependent, unverifiable signals.** Neither HLS's
   `#EXT-X-DISCONTINUITY` nor any DASH-native signal is set automatically on an encoder restart — it
   requires the origin to explicitly configure tagging (ffmpeg's `-hls_flags +discont_start`). A real test
   confirmed: a genuine encoder restart with a resolution/GOP change, without that flag, produced zero
   discontinuity tags. Program-Date-Time is the same story — ffmpeg's default emits none; it requires
   `#EXT-X-PROGRAM-DATE-TIME` to be explicitly enabled at the origin. A consumer has no independent way to
   verify either signal; both are "the origin didn't say otherwise," not a guarantee.

## Decision

### `MediaSegment` — `openframe.core.media`

Added to the same `openframe.core.media` module as `MediaKind`/`MediaFrame`, as a new file
(`openframe/core/media/segment.py`) following the same split `frame.py` already established, re-exported
from the module's `__init__.py` alongside the existing two names. Frozen, `slots=True` dataclass, same
convention as `MediaFrame`.

**The real distinction from `MediaFrame`:** a `MediaFrame` is one classified, already-demuxed
elementary-stream unit (one video NAL unit, one audio packet) — `MediaKind` already tells you which. A
`MediaSegment` is one undemuxed, muxed container holding multiple elementary streams together (a whole
`.m4s`/`.ts` file, audio and video interleaved). Turning a `MediaSegment` into its constituent `MediaFrame`s
requires real container demuxing — parsing fMP4 boxes or MPEG-TS packets and splitting out each elementary
stream. That work stays out of `openframe-protocol-media`'s scope, for the exact reason ADR-009 already
gives for keeping transcoding out of that package: it's ffmpeg/container-parsing work that belongs in the
consumer's own adapter (a future `openframe-adapters-media-ffmpeg`), not in the protocol package that just
moves bytes.

Key field decisions, driven directly by the two spikes above:

- **`sequence: int` must be used for de-duplication, never the segment's URI.** Backed by the spike
  confirming HLS `media_sequence` and DASH's resolved segment number are both reliable, and the separate
  spike confirming URIs are not (encoder restarts reset filename counters, causing URI reuse across
  unrelated segments).
- **`discontinuity: bool = False` is documented as a weak signal, not a guarantee.** `discontinuity=False`
  means "the origin didn't say otherwise," not "definitely contiguous" — confirmed by the spike showing a
  genuine encoder restart produced zero discontinuity tags without explicit origin-side configuration. A
  pull client may additionally set this to `True` from its own sequence-gap detection (inferred
  discontinuity); that's `-media`-level pull-loop behavior, not something this dataclass enforces.
- **`program_date_time_ms: int | None = None` is informational only, never an ordering mechanism.**
  `sequence` determines play order; this field is wall-clock sync/correlation metadata, `None` when the
  origin doesn't provide enough information — confirmed by the spike showing it, too, depends on explicit
  origin-side tagging ffmpeg doesn't enable by default.
- **`payload: bytes`, not `memoryview`**, for the same reason as `MediaFrame.payload` — a segment is
  expected to outlive the fetch callback that created it, so an owned copy avoids a use-after-free class of
  bug.
- **`duration_ms: int`** carries the manifest-declared nominal duration (HLS `#EXTINF`, DASH
  `SegmentTimeline`'s `d`), for live-edge/DVR-window calculations.
- **`representation_id: str | None = None`** identifies which rendition/adaptation set a segment came from,
  mirroring `MediaFrame.track`'s "reserve the field now, no current multi-X producer" reasoning for
  multi-rendition streams.
- **`received_at_ns: int = 0`** mirrors `MediaFrame.received_at_ns` exactly — local fetch-latency/dwell-time
  metrics, distinct from the manifest-provided timeline fields.

## Consequences

- **New file `openframe/core/media/segment.py`** exports `MediaSegment`, re-exported from
  `openframe/core/media/__init__.py` alongside `MediaKind`/`MediaFrame`. Module docstring updated to
  describe both frame and segment vocabularies. Still marked `.. stability: experimental`.
- **No change to any existing contract.** `MediaKind`/`MediaFrame` are untouched.
- **Version bump: `3.9.0` → `3.10.0`** — additive, non-breaking minor version.

## Alternatives considered

- **Define `MediaSegment` inside `openframe-protocol-media` itself.** Rejected, for the identical reason
  ADR-009 rejected this for `MediaFrame`: a future `openframe-adapters-media-ffmpeg` package would have to
  depend on `openframe-protocol-media` purely to share a data shape.
- **Have the pull client demux segments into `MediaFrame`s itself, so only `MediaFrame` ever needs to
  exist.** Rejected: demuxing is real container-parsing work (fMP4 box parsing or MPEG-TS packet parsing),
  not something `openframe-protocol-media` should take on — the same "transcoding stays out of the protocol
  package" boundary ADR-009 already drew for the RTMP side applies symmetrically to the pull side.
- **Treat `discontinuity`/`program_date_time_ms` as reliable signals a consumer can branch on with
  confidence.** Rejected — both real spikes found these require origin-side configuration no protocol
  package can verify or control, so the fields are documented as weak/informational rather than given any
  stronger contract they can't actually honor.
