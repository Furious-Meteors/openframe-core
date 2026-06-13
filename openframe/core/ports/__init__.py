"""
openframe/core/ports/
======================
Generic Protocol ports for the OpenFrame ecosystem.

Every adapter package implements one or more of these protocols structurally
(no inheritance needed). Services depend only on these ports — never on
concrete adapter implementations.

Usage::

    from openframe.core.ports import BaseRepository, BaseProducer, BaseConsumer

Runtime isinstance checks::

    isinstance(repo, BaseRepository)   # ✓ works
    isinstance(repo, BaseRepository[str])  # ✗ raises TypeError — use unparameterised form
"""
from __future__ import annotations

from openframe.core.ports.consumer import BaseConsumer
from openframe.core.ports.producer import BaseProducer
from openframe.core.ports.repository import BaseRepository

__all__ = [
    "BaseRepository",
    "BaseProducer",
    "BaseConsumer",
]
