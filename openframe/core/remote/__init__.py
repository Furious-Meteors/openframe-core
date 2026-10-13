"""
openframe.core.remote
========================
Outbound counterparts of openframe.core.inbound's CommandHandler/
QueryHandler — contracts for a service calling *another service built on
this platform*, as opposed to `openframe.core.ports.outbound` (third-party
backend adapters, Capability-tagged) or `openframe.core.inbound`
(callers reaching into this service).

Added for openframe-protocol's M1b (HTTP client) — see that repo's design
spec draft 8, section 5.6, decision D10. No BasePort/Capability
involvement; see `client.py`'s own docstring for why.

.. stability: experimental
   New alongside the first concrete implementation
   (`openframe-protocol-http`'s `HttpRemoteQueryClient`/
   `HttpRemoteCommandClient`). API may change based on real usage.
"""
from __future__ import annotations

from openframe.core.remote.client import RemoteCommandClient, RemoteQueryClient

__all__ = ["RemoteCommandClient", "RemoteQueryClient"]
