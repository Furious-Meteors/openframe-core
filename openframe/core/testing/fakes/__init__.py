"""
openframe.core.testing.fakes
==============================
In-memory test doubles for OpenFrame ports.

All fakes have zero external dependencies and satisfy their respective
port protocols via structural subtyping.

.. stability: beta
"""
from __future__ import annotations

from openframe.core.testing.fakes.consumer import FakeConsumer
from openframe.core.testing.fakes.producer import FakeProducer
from openframe.core.testing.fakes.repository import InMemoryRepository

__all__ = [
    "InMemoryRepository",
    "FakeProducer",
    "FakeConsumer",
]
