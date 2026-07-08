"""
openframe.core.testing.fakes
==============================
In-memory test doubles for OpenFrame ports and inbound contracts (ADR-006).

Outbound fakes (``InMemoryRepository``, ``FakeProducer``, ``FakeConsumer``)
have zero external dependencies and satisfy their respective
``BasePort``-based port protocols via structural subtyping — including the
identity/lifecycle members every port now carries.

Inbound fakes (``EchoUseCase``, ``SpyCommandHandler``, ``SpyQueryHandler``)
mirror the outbound fakes for the driving side of the hexagon — they
satisfy ``UseCase``/``CommandHandler``/``QueryHandler`` structurally and
record every call for spy-style assertions.

.. stability: beta
"""
from __future__ import annotations

from openframe.core.testing.fakes.consumer import FakeConsumer
from openframe.core.testing.fakes.inbound import (
    EchoUseCase,
    SpyCommandHandler,
    SpyQueryHandler,
)
from openframe.core.testing.fakes.producer import FakeProducer
from openframe.core.testing.fakes.repository import InMemoryRepository

__all__ = [
    "InMemoryRepository",
    "FakeProducer",
    "FakeConsumer",
    "EchoUseCase",
    "SpyCommandHandler",
    "SpyQueryHandler",
]
