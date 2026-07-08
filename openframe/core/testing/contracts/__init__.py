"""
openframe.core.testing.contracts
==================================
Reusable pytest base classes for port and inbound contract tests (ADR-006).

Outbound: ``PortContractTests``/``LifecycleContractTests`` cover the
shared ``BasePort`` identity/lifecycle suite; ``RepositoryContractTests``,
``ProducerContractTests``, ``ConsumerContractTests`` build on
``PortContractTests`` with domain-specific assertions.

Inbound: ``UseCaseContractTests``, ``CommandHandlerContractTests``,
``QueryHandlerContractTests`` mirror the outbound contract classes for
the driving side of the hexagon. They do not build on any shared base
class — ``UseCase``/``CommandHandler``/``QueryHandler`` do not extend
``BasePort``.

No top-level pytest import — all modules here can be imported without
pytest installed.

.. stability: beta
"""
from __future__ import annotations

from openframe.core.testing.contracts.consumer import ConsumerContractTests
from openframe.core.testing.contracts.inbound import (
    CommandHandlerContractTests,
    QueryHandlerContractTests,
    UseCaseContractTests,
)
from openframe.core.testing.contracts.lifecycle import LifecycleContractTests
from openframe.core.testing.contracts.port import PortContractTests
from openframe.core.testing.contracts.producer import ProducerContractTests
from openframe.core.testing.contracts.repository import RepositoryContractTests

__all__ = [
    "LifecycleContractTests",
    "PortContractTests",
    "RepositoryContractTests",
    "ProducerContractTests",
    "ConsumerContractTests",
    "UseCaseContractTests",
    "CommandHandlerContractTests",
    "QueryHandlerContractTests",
]
