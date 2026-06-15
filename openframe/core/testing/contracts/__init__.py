"""
openframe.core.testing.contracts
==================================
Reusable pytest base classes for port contract tests.

No top-level pytest import — all modules here can be imported without
pytest installed.

.. stability: beta
"""
from __future__ import annotations

from openframe.core.testing.contracts.consumer import ConsumerContractTests
from openframe.core.testing.contracts.producer import ProducerContractTests
from openframe.core.testing.contracts.repository import RepositoryContractTests

__all__ = [
    "RepositoryContractTests",
    "ProducerContractTests",
    "ConsumerContractTests",
]
