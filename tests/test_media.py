"""
tests/test_media.py
=======================
Coverage for `openframe.core.media` — `MediaKind`, `MediaFrame`,
`MediaSegment`.
"""
from __future__ import annotations

import dataclasses

import pytest

from openframe.core.media import MediaFrame, MediaKind, MediaSegment

# ---------------------------------------------------------------------------
# MediaKind
# ---------------------------------------------------------------------------


def test_media_kind_has_expected_members() -> None:
    assert {m.name for m in MediaKind} == {"VIDEO", "AUDIO", "METADATA"}


def test_media_kind_values() -> None:
    assert MediaKind.VIDEO == "video"
    assert MediaKind.AUDIO == "audio"
    assert MediaKind.METADATA == "metadata"


# ---------------------------------------------------------------------------
# MediaFrame
# ---------------------------------------------------------------------------


def test_media_frame_is_frozen() -> None:
    frame = MediaFrame(kind=MediaKind.VIDEO, payload=b"\x00\x01", timestamp_ms=1000)
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        frame.timestamp_ms = 2000  # type: ignore[misc]


def test_media_frame_defaults() -> None:
    frame = MediaFrame(kind=MediaKind.AUDIO, payload=b"\x01\x02\x03", timestamp_ms=500)
    assert frame.track == "default"
    assert frame.is_keyframe is False
    assert frame.is_config is False
    assert frame.received_at_ns == 0
    assert frame.codec is None


def test_media_frame_constructs_with_all_fields() -> None:
    frame = MediaFrame(
        kind=MediaKind.VIDEO,
        payload=b"\xde\xad\xbe\xef",
        timestamp_ms=123456,
        is_keyframe=True,
        is_config=True,
        codec="h264",
        track="primary",
        received_at_ns=987654321,
    )
    assert frame.kind is MediaKind.VIDEO
    assert frame.payload == b"\xde\xad\xbe\xef"
    assert frame.timestamp_ms == 123456
    assert frame.is_keyframe is True
    assert frame.is_config is True
    assert frame.codec == "h264"
    assert frame.track == "primary"
    assert frame.received_at_ns == 987654321


# ---------------------------------------------------------------------------
# MediaSegment
# ---------------------------------------------------------------------------


def test_media_segment_is_frozen() -> None:
    segment = MediaSegment(payload=b"\x00\x01", sequence=1, duration_ms=6000)
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        segment.sequence = 2  # type: ignore[misc]


def test_media_segment_defaults() -> None:
    segment = MediaSegment(payload=b"\x01\x02\x03", sequence=42, duration_ms=4000)
    assert segment.discontinuity is False
    assert segment.program_date_time_ms is None
    assert segment.representation_id is None
    assert segment.received_at_ns == 0


def test_media_segment_constructs_with_all_fields() -> None:
    segment = MediaSegment(
        payload=b"\xde\xad\xbe\xef",
        sequence=123,
        duration_ms=6000,
        discontinuity=True,
        program_date_time_ms=1_700_000_000_000,
        representation_id="720p",
        received_at_ns=987654321,
    )
    assert segment.payload == b"\xde\xad\xbe\xef"
    assert segment.sequence == 123
    assert segment.duration_ms == 6000
    assert segment.discontinuity is True
    assert segment.program_date_time_ms == 1_700_000_000_000
    assert segment.representation_id == "720p"
    assert segment.received_at_ns == 987654321
