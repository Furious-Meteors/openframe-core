"""
openframe/core/media/frame.py
==================================
`MediaKind`, `MediaFrame` — the shared frame vocabulary for binary media
transports (RTMP ingest, HLS/DASH delivery, and whatever ffmpeg-backed
adapters consume them downstream). See this module's own `__init__.py`
and ADR-009 for why this lives in `openframe-core` rather than in
`openframe-protocol-media` or a future `openframe-adapters-media-ffmpeg`.

Dependency order: this module imports only from Python stdlib.
No openframe.core imports.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

__all__ = ["MediaKind", "MediaFrame"]


class MediaKind(StrEnum):
    """
    Structural category of a `MediaFrame`'s payload.

    Deliberately a small, genuinely closed set — unlike `MediaFrame.codec`
    (see that field's docstring), video/audio/metadata are structural
    categories of a media session, not something that grows per-codec.

    Members:
        VIDEO:    A video elementary-stream frame (e.g. an H.264/HEVC
                  NAL unit or AV1 OBU).
        AUDIO:    An audio elementary-stream frame (e.g. an AAC/Opus
                  packet).
        METADATA: Reserved for future use — e.g. a gap/discontinuity
                  marker a producer might need to signal downstream.
                  No producer or consumer in this codebase emits or
                  handles `METADATA` frames yet; the member exists so
                  adding that capability later doesn't require widening
                  this enum (a breaking change for anyone matching on it
                  exhaustively).
    """

    VIDEO = "video"
    AUDIO = "audio"
    METADATA = "metadata"


@dataclass(frozen=True, slots=True)
class MediaFrame:
    """
    One discrete unit of media handed from a producer (e.g. an RTMP
    ingest handler) to a consumer (e.g. an HLS/DASH packager or a
    recording sink). Immutable — a frame is a fact about something that
    already happened (a packet arrived), not a mutable buffer a consumer
    edits in place.

    Fields:
        kind: Structural category of `payload` — see `MediaKind`.

        payload: The raw encoded bytes for this frame. Deliberately
            `bytes`, not `memoryview`. A producer (e.g. pyrtmp) typically
            hands back a payload sliced out of a buffer it owns and may
            reuse for the next packet it reads off the socket. A
            `MediaFrame` is expected to outlive the callback that created
            it — it typically sits in a queue until a consumer drains it
            — so a `memoryview` into a buffer the producer goes on to
            overwrite would be a use-after-free class of bug: the frame
            would silently change (or corrupt) after construction. `bytes`
            is an owned copy, so a frame's `payload` is guaranteed to mean
            what it meant when the frame was built, for as long as the
            frame exists. `len(payload)` is the canonical byte-budget unit
            for any consumer doing byte-based buffering — there is
            deliberately no separate `size`/`length` field that could
            drift from the real payload.

        timestamp_ms: Source-clock timestamp, in milliseconds, as carried
            by the original stream (e.g. an RTMP/FLV tag timestamp). Used
            for duration-based budgeting and for audio/video sync —
            distinct from `received_at_ns`, which is about local
            processing latency, not the media timeline.

        is_keyframe: Whether this frame can be decoded without reference
            to prior frames (e.g. an H.264 IDR frame). Defaults to
            `False`. A consumer shedding frames under backpressure can
            usually resync at the next keyframe, so dropping a
            non-keyframe is often tolerable — see `is_config` below for
            the frame kind where that is never true.

        is_config: Whether this frame is a sequence header / codec
            configuration record (e.g. an AVCDecoderConfigurationRecord
            or an AAC `AudioSpecificConfig`), rather than ordinary media
            data. Deliberately a separate field from `is_keyframe`, and a
            *strictly stronger* invariant: dropping a keyframe makes a
            stream corrupt until the next keyframe arrives, but dropping
            a config frame can make the entire stream undecodable with no
            recovery short of a brand-new session. Any future consumer
            that sheds frames under backpressure must never drop a frame
            where `is_config` is `True`, under any shedding policy.
            Defaults to `False`.

        codec: The codec this frame's `payload` is encoded with (e.g.
            `"h264"`, `"hevc"`, `"av1"`, `"aac"`, `"opus"`), or `None`
            when not yet known (e.g. before the first config frame has
            been seen). Deliberately a plain `str | None`, not a closed
            enum — codecs proliferate over time, and a closed enum living
            in `openframe-core` would demand a core release every time a
            new codec needs support. This mirrors this repo's own
            existing precedent for error codes
            (`openframe.core.exceptions.codes.ErrorCode`): that taxonomy
            is typed `str` specifically so the vocabulary can grow
            per-package without a central registry every package must
            edit, and the same reasoning applies here.

        track: Track identifier, for multi-bitrate or multi-audio-track
            streams. Defaults to `"default"`. No producer or consumer in
            this codebase currently emits more than one track, but
            reserving the field now costs nothing and avoids a breaking
            field addition later, once multi-track support is actually
            built.

        received_at_ns: `time.perf_counter_ns()` (or equivalent monotonic
            clock) at the point this frame arrived locally. Defaults to
            `0`, meaning "not recorded." This is the only way a consumer
            can measure how long a frame sat in a queue before being
            processed — dwell-time metrics — since `timestamp_ms` is a
            source-clock value with no fixed relationship to local wall
            time.
    """

    kind: MediaKind
    payload: bytes
    timestamp_ms: int
    is_keyframe: bool = False
    is_config: bool = False
    codec: str | None = None
    track: str = "default"
    received_at_ns: int = 0
