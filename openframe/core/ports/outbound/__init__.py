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

Future outbound capabilities (openframe-infra: ``BaseSecretsProvider``,
``BaseObjectStore``, ``BaseFeatureFlagProvider``) will be added here
as the ecosystem grows — this sub-module is the canonical home for any
outbound port protocol that targets a specific capability.

These are abstract structural Protocols — no concrete code.
Implementations live in openframe-adapters.

Usage::

    from openframe.core.ports import BaseRepository, BaseProducer, BaseConsumer

Or via explicit path if needed::

    from openframe.core.ports.outbound import BaseRepository
"""
from __future__ import annotations

from openframe.core.ports.outbound.consumer import BaseConsumer
from openframe.core.ports.outbound.producer import BaseProducer
from openframe.core.ports.outbound.repository import BaseRepository

__all__ = ["BaseRepository", "BaseProducer", "BaseConsumer"]
