"""
openframe/core/ports/outbound/
================================
Capability-specific outbound port protocols — the driven side of the
hexagon.

Each protocol extends :class:`~openframe.core.ports.port.BasePort`
(Identity + Lifecycle) and adds the domain methods specific to one
outbound capability:

- :class:`~openframe.core.ports.outbound.repository.BaseRepository` —
  CRUD persistence (``PERSISTENCE`` capability).
- :class:`~openframe.core.ports.outbound.producer.BaseProducer` —
  message publishing (``QUEUE`` capability).
- :class:`~openframe.core.ports.outbound.consumer.BaseConsumer` —
  message consumption (``QUEUE`` capability).
- :class:`~openframe.core.ports.outbound.repository.BaseVectorStore` —
  id-addressable CRUD plus similarity search (``SEARCH`` capability).
  Extends ``BaseRepository`` directly (defined in the same module) rather
  than sitting as a sibling of it — see ``repository.py``'s own
  docstring for why.
- :class:`~openframe.core.ports.outbound.repository.BaseGraphStore` —
  id-addressable node CRUD plus pattern-matching traversal (``SEARCH``
  capability). Also extends ``BaseRepository`` directly (defined in the
  same module) — see ``repository.py``'s own docstring for why, and for
  why relationships/edges are not given their own port method.

Future outbound capabilities (openframe-infra: ``BaseSecretsProvider``,
``BaseObjectStore``, ``BaseFeatureFlagProvider``) will be added here
as the ecosystem grows — this sub-module is the canonical home for any
outbound port protocol that targets a specific capability.

These are abstract structural Protocols — no concrete code.
Implementations live in openframe-adapters.

Usage::

    from openframe.core.ports import BaseRepository, BaseProducer, BaseConsumer, BaseVectorStore, BaseGraphStore

Or via explicit path if needed::

    from openframe.core.ports.outbound import BaseRepository
"""
from __future__ import annotations

from openframe.core.ports.outbound.consumer import BaseConsumer
from openframe.core.ports.outbound.producer import BaseProducer
from openframe.core.ports.outbound.repository import (
    BaseGraphStore,
    BaseRepository,
    BaseVectorStore,
)

__all__ = [
    "BaseRepository",
    "BaseProducer",
    "BaseConsumer",
    "BaseVectorStore",
    "BaseGraphStore",
]
