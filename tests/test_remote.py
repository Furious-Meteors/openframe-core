"""
tests/test_remote.py
=======================
Tests for openframe.core.remote and its contract tests.

Deliberately reuses SpyCommandHandler/SpyQueryHandler (openframe.core.testing's
own inbound fakes) as the remote-client fixtures here, rather than adding
new fakes — RemoteCommandClient/RemoteQueryClient have the identical
execute() shape CommandHandler/QueryHandler already do (see
remote/client.py's own docstring for why they're still separate Protocol
classes despite that), so the existing fakes already satisfy both
structurally. Kept in its own file, not folded into test_testing_fakes.py,
because blending inbound and outbound fixtures in one file would blur
exactly the direction distinction this module exists to preserve.
"""
from __future__ import annotations

import pytest

from openframe.core.remote import RemoteCommandClient, RemoteQueryClient
from openframe.core.testing import (
    RemoteCommandClientContractTests,
    RemoteQueryClientContractTests,
    SpyCommandHandler,
    SpyQueryHandler,
)


class TestSpyCommandHandlerAsRemoteCommandClient(RemoteCommandClientContractTests):
    """SpyCommandHandler, unchanged, also satisfies RemoteCommandClient."""

    @pytest.fixture
    def command_handler(self) -> SpyCommandHandler:
        return SpyCommandHandler()


class TestSpyQueryHandlerAsRemoteQueryClient(RemoteQueryClientContractTests):
    """SpyQueryHandler, configured with a response, also satisfies RemoteQueryClient."""

    @pytest.fixture
    def query_handler(self) -> SpyQueryHandler:
        return SpyQueryHandler(response={"id": "remote-1"})


def test_spy_command_handler_satisfies_remote_command_client_directly() -> None:
    assert isinstance(SpyCommandHandler(), RemoteCommandClient)


def test_spy_query_handler_satisfies_remote_query_client_directly() -> None:
    assert isinstance(SpyQueryHandler(), RemoteQueryClient)


def test_command_handler_and_remote_command_client_are_distinct_classes() -> None:
    """
    Structurally identical, but deliberately not the same class or an
    alias of one another — see remote/client.py's own docstring.
    """
    from openframe.core.inbound import CommandHandler

    assert CommandHandler is not RemoteCommandClient


def test_query_handler_and_remote_query_client_are_distinct_classes() -> None:
    from openframe.core.inbound import QueryHandler

    assert QueryHandler is not RemoteQueryClient
