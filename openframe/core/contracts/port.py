"""
openframe/core/contracts/port.py
===================================
BasePort — the single unified outbound contract (ADR-006).

``BasePort`` combines :class:`~openframe.core.contracts.identity.Identity`
and :class:`~openframe.core.contracts.lifecycle.Lifecycle`. It is the one
base every outbound port in ``openframe.core.ports`` extends, and the one
type the plugin registry accepts — there is no separate "plugin" protocol.
A plugin *is* a registered ``BasePort``.

Runtime isinstance check::

    isinstance(adapter, BasePort)   # ✓ works
    isinstance(adapter, BasePort[str])  # not applicable — BasePort itself
                                         # is not generic; concrete ports
                                         # like BaseRepository[T] are.

Dependency order:
    contracts/identity  → contracts/capability
    contracts/lifecycle → contracts/health → contracts/context
    contracts/port      → contracts/identity + contracts/lifecycle
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from openframe.core.contracts.identity import Identity
from openframe.core.contracts.lifecycle import Lifecycle

__all__ = ["BasePort"]


@runtime_checkable
class BasePort(Identity, Lifecycle, Protocol):
    """
    Unified outbound contract: Identity + Lifecycle.

    Every outbound port (``BaseRepository``, ``BaseProducer``,
    ``BaseConsumer``, and any future port package defines) extends this
    directly, gaining ``name``/``version``/``capability`` and
    ``initialize``/``shutdown``/``health`` for free alongside its own
    domain-specific methods.

    Adapters satisfy this protocol structurally — no inheritance from
    ``BasePort`` is required or desired.
    """
