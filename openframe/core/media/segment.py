"""
openframe/core/media/segment.py
==================================
`MediaSegment` — the shared vocabulary for one fetched HLS/DASH segment
file, as consumed by a pull/poll client (`openframe-protocol-media`'s
future HLS/DASH puller) and a downstream demuxing adapter (a future
`openframe-adapters-media-ffmpeg`). See this module's own `__init__.py`
and ADR-010 for why this lives alongside `MediaFrame` in
`openframe-core` rather than in `openframe-protocol-media` or the
adapters package.

Dependency order: this module imports only from Python stdlib.
No openframe.core imports.
"""
from __future__ import annotations

from dataclasses import dataclass

__all__ = ["MediaSegment"]


@dataclass(frozen=True, slots=True)
class MediaSegment:
    """
    One whole segment file fetched from an HLS or DASH manifest (an
    fMP4/CMAF `.m4s` or MPEG-TS `.ts` file) — a muxed container holding
    both audio and video together, not yet split into per-stream
    `MediaFrame`s. Immutable — a segment is a fact about something that
    already happened (a fetch completed), not a mutable buffer a
    consumer edits in place.

    Fields:
        payload: The undemuxed container bytes for this segment. Unlike
            `MediaFrame.payload`, which is already one classified
            elementary-stream unit, a single `MediaSegment.payload`
            holds audio AND video muxed together. Turning it into
            separate `MediaFrame`s requires real container demuxing,
            which is deliberately not this package's job — the same
            "transcoding stays out of `openframe-protocol-media`"
            reasoning `MediaFrame`'s own docstring and ADR-009 already
            give applies here too; that work belongs in the consumer's
            own ffmpeg-backed adapter. Deliberately `bytes`, not
            `memoryview`, for the same reason as `MediaFrame.payload`:
            a segment is expected to outlive the fetch callback that
            created it (it typically sits in a queue until a consumer
            drains it), so an owned copy avoids a use-after-free class
            of bug where the segment's data could silently change after
            construction.

        sequence: Absolute, monotonically increasing sequence number —
            HLS's `media_sequence` (confirmed reliable for dedup by a
            real spike: the `m3u8` library assigns this per-segment
            automatically) or DASH's resolved segment number from
            `SegmentTemplate`/`SegmentTimeline` (confirmed by a real
            spike: hand-resolved and verified byte-for-byte against 80
            real segments, zero mismatches). Must be used for
            de-duplication, never the segment's URI — a spike confirmed
            URIs can repeat across an unrelated stream/encoder restart
            (segment filename counters reset), so dedup-by-URI would
            silently treat two genuinely different segments as the same
            one.

        duration_ms: The segment's nominal duration, in milliseconds, as
            declared by the manifest (HLS `#EXTINF`, DASH
            `SegmentTimeline`'s `d` value). Used for live-edge/DVR-window
            calculations.

        discontinuity: Whether this segment is known to be discontinuous
            with the previous one (e.g. an encoder restart, a
            resolution/codec change). Defaults to `False`. A real spike
            found this is a weak signal: neither HLS's
            `#EXT-X-DISCONTINUITY` nor any DASH-native signal is ever
            set automatically — it depends entirely on the origin
            encoder explicitly configuring discontinuity tagging
            (ffmpeg's own `-hls_flags +discont_start`, confirmed
            required; without it, a genuine encoder restart with a
            resolution/GOP change produced zero discontinuity tags in a
            real test). A consumer cannot assume `discontinuity=False`
            means "definitely contiguous" — it means "the origin didn't
            say otherwise," which is weaker. A pull client may
            additionally set this to `True` when it detects a
            sequence-number gap itself (inferred discontinuity,
            independent of origin tagging) — that is a
            `-media`-level pull-loop behavior, not something this
            dataclass enforces.

        program_date_time_ms: Wall-clock timestamp (Unix epoch
            milliseconds) this segment corresponds to, when known —
            HLS's Program-Date-Time (confirmed by a real spike to
            require the origin's `#EXT-X-PROGRAM-DATE-TIME` tagging to
            be enabled at all; ffmpeg's default emits none) or DASH's
            equivalent derived from `availabilityStartTime` plus segment
            timeline position. `None` when the origin doesn't provide
            enough information to compute it. This is wall-clock
            sync/correlation metadata only, not a segment-ordering
            mechanism — `sequence` is what determines play order.

        representation_id: Which rendition/adaptation set (HLS variant
            stream, DASH `Representation`) this segment came from, when
            the stream has more than one. `None` for a single-rendition
            stream or when not yet resolved.

        received_at_ns: `time.perf_counter_ns()` (or equivalent monotonic
            clock) at the point this segment was fetched locally.
            Defaults to `0`, meaning "not recorded." Mirrors
            `MediaFrame.received_at_ns`'s own reasoning: this is for
            dwell-time/fetch-latency metrics, distinct from the
            manifest-provided `duration_ms`/`program_date_time_ms`,
            which describe the media timeline, not local processing
            time.
    """

    payload: bytes
    sequence: int
    duration_ms: int
    discontinuity: bool = False
    program_date_time_ms: int | None = None
    representation_id: str | None = None
    received_at_ns: int = 0
