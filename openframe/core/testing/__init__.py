"""
openframe.core.testing
=======================
Reusable testing infrastructure for the OpenFrame ecosystem.

Provides in-memory test doubles (fakes) and reusable pytest base classes
(contract tests) that every ``openframe-adapters-*`` package uses.

Zero external dependencies — fakes import only from
``openframe.core.ports``, ``openframe.core.health``, and
``openframe.core.exceptions``.  Contract test classes do not import pytest
at the module level; they are only useful when pytest is installed.

.. stability: beta
   Beta — API may change in minor versions with a deprecation notice.

Quick reference::

    from openframe.core.testing import InMemoryRepository, FakeProducer, FakeConsumer
    from openframe.core.testing import RepositoryContractTests

    repo = InMemoryRepository()
    assert isinstance(repo, BaseRepository)
    assert isinstance(repo, HealthCheck)
"""
from __future__ import annotations

from openframe.core.testing.contracts.consumer import ConsumerContractTests
from openframe.core.testing.contracts.producer import ProducerContractTests
from openframe.core.testing.contracts.repository import RepositoryContractTests
from openframe.core.testing.fakes.consumer import FakeConsumer
from openframe.core.testing.fakes.producer import FakeProducer
from openframe.core.testing.fakes.repository import InMemoryRepository

__all__ = [
    "InMemoryRepository",
    "FakeProducer",
    "FakeConsumer",
    "RepositoryContractTests",
    "ProducerContractTests",
    "ConsumerContractTests",
]
