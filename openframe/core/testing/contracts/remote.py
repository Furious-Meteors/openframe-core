"""
openframe/core/testing/contracts/remote.py
=============================================
RemoteCommandClientContractTests, RemoteQueryClientContractTests —
reusable pytest base classes for `openframe.core.remote`'s outbound
contracts.

Extends `CommandHandlerContractTests`/`QueryHandlerContractTests` rather
than duplicating their test bodies — `RemoteCommandClient`/
`RemoteQueryClient` have the identical `execute()` shape (see
`remote/client.py`'s own docstring for why they're still separate
Protocol classes despite that). Only the protocol-conformance assertion
differs; every other test (return-type shape, context handling) is
inherited unchanged.

No top-level pytest import — importable without pytest installed,
matching every other contract module's own convention.

Dependency order:
    testing/contracts/remote → testing/contracts/inbound, remote

Subclass usage::

    class TestMyRemoteQueryClient(RemoteQueryClientContractTests):
        @pytest.fixture
        def query_handler(self) -> MyRemoteQueryClient:
            return MyRemoteQueryClient()
"""
from __future__ import annotations

from openframe.core.testing.contracts.inbound import (
    CommandHandlerContractTests,
    QueryHandlerContractTests,
)

__all__ = ["RemoteCommandClientContractTests", "RemoteQueryClientContractTests"]


class RemoteCommandClientContractTests(CommandHandlerContractTests):
    """
    Reusable pytest base class for
    :class:`~openframe.core.remote.RemoteCommandClient` contract tests.

    Subclasses must provide the same `command_handler` fixture
    `CommandHandlerContractTests` itself requires — the fixture name is
    unchanged, only the protocol being checked is.

    .. stability: experimental
    """

    async def test_satisfies_command_handler_protocol(self, command_handler) -> None:
        """Overridden: checks RemoteCommandClient, not CommandHandler."""
        from openframe.core.remote import RemoteCommandClient

        assert isinstance(command_handler, RemoteCommandClient), (
            f"{type(command_handler).__name__} does not satisfy RemoteCommandClient. "
            "Ensure it has a matching async 'execute' method."
        )


class RemoteQueryClientContractTests(QueryHandlerContractTests):
    """
    Reusable pytest base class for
    :class:`~openframe.core.remote.RemoteQueryClient` contract tests.

    Subclasses must provide the same `query_handler`/`make_query`
    fixtures `QueryHandlerContractTests` itself requires.

    .. stability: experimental
    """

    async def test_satisfies_query_handler_protocol(self, query_handler) -> None:
        """Overridden: checks RemoteQueryClient, not QueryHandler."""
        from openframe.core.remote import RemoteQueryClient

        assert isinstance(query_handler, RemoteQueryClient), (
            f"{type(query_handler).__name__} does not satisfy RemoteQueryClient. "
            "Ensure it has a matching async 'execute' method."
        )
