"""
openframe/core/ports/transportation.py
============================================
Closed taxonomy of network transport protocols shipped (or about to ship)
across the OpenFrame ecosystem.

`Transportation` was originally proposed in `openframe-protocol`'s own
design spec, years before any transport shipped — but nothing in that spec
*forced* it to exist before now. Six transports (HTTP, gRPC, SSE,
WebSocket, webhooks, QUIC) have since shipped as concrete packages without
ever needing a shared enum to name them by; each one simply didn't require
cross-transport comparison against the others. That changes with
`openframe-protocol-media` (RTMP ingest, HLS/DASH delivery) on the near
horizon — a `MediaFrame`-carrying family of transports that benefits from
being named alongside the existing six in one place. This enum is a pure,
additive backfill of that years-old proposal: it has zero consumers today,
breaks nothing by existing, and the six already-shipped transports are
added here as members purely for completeness, not because anything in
this codebase requires it of them yet. See
`docs/technical/architecture/adrs/adr-009-media-frame-and-transportation.md`
for the full rationale, including why `Capability.TRANSPORT`'s removal
(bundled with this enum in that old design doc) is deliberately deferred
to a future major version.

Dependency order: this module imports only from Python stdlib.
No openframe.core imports.
"""
from __future__ import annotations

from enum import Enum

__all__ = ["Transportation"]


class Transportation(str, Enum):
    """
    Closed taxonomy of network transport protocols.

    Subclasses ``str`` so members compare equal to their value
    (``Transportation.HTTP == "http"``) and serialise cleanly to JSON/logs
    without an explicit ``.value`` access.

    Members:
        HTTP:      Request/response over HTTP.
        GRPC:      Request/response (and streaming) over gRPC.
        SSE:       Server-Sent Events — unidirectional, server→client.
        WEBSOCKET: Bidirectional, long-lived socket connection.
        WEBHOOK:   Server-to-server callback delivered over HTTP.
        QUIC:      Transport over the QUIC protocol (HTTP/3 and beyond).
        RTMP:      Real-Time Messaging Protocol, used for live media ingest.
        RTSP:      Real Time Streaming Protocol session control
                   (reserved — no server implementation ships yet).
        HLS:       HTTP Live Streaming, segmented media delivery over HTTP.
        DASH:      Dynamic Adaptive Streaming over HTTP.
    """

    HTTP = "http"
    GRPC = "grpc"
    SSE = "sse"
    WEBSOCKET = "websocket"
    WEBHOOK = "webhook"
    QUIC = "quic"
    RTMP = "rtmp"
    RTSP = "rtsp"
    HLS = "hls"
    DASH = "dash"

    def __str__(self) -> str:
        return self.value
