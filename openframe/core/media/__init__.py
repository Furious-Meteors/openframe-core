"""
openframe.core.media
========================
Shared media vocabulary for binary media transports — `MediaKind`/
`MediaFrame` for classified, already-demuxed elementary-stream units (RTMP
ingest), and `MediaSegment` for whole, undemuxed HLS/DASH segment files
(pull/poll delivery). Added ahead of `openframe-protocol-media` (RTMP
ingest, HLS/DASH delivery), which carries high-density binary audio/video
packets and needs shared types a future, separate
`openframe-adapters-media-ffmpeg` package can also import. That shared
vocabulary has to live in core: putting it in the protocol package would
force the adapters package to depend on the protocol package (or vice
versa) purely to share data shapes, inverting the hexagon's dependency
direction between two sibling families that otherwise have no reason to
know about each other. See
`docs/technical/architecture/adrs/adr-009-media-frame-and-transportation.md`
for `MediaFrame`'s design rationale and
`docs/technical/architecture/adrs/adr-010-media-segment.md` for
`MediaSegment`'s.

No BasePort/Capability involvement — both types are plain, immutable
data carriers passed between a producer and a consumer that already know
each other by direct construction, the same reasoning `openframe.core.remote`
gives for staying out of the Capability-based registry lookup machinery.

.. stability: experimental
   New alongside the first concrete producer (`openframe-protocol-media`'s
   RTMP ingest). API may change based on real usage.
"""
from __future__ import annotations

from openframe.core.media.frame import MediaFrame, MediaKind
from openframe.core.media.segment import MediaSegment

__all__ = ["MediaKind", "MediaFrame", "MediaSegment"]
