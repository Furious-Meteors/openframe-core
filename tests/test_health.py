"""
tests/test_health.py
======================
Tests for openframe.core.health — HealthCheck Protocol.

Covers:
- Classes implementing both ping() and is_ready() satisfy HealthCheck
- Classes missing either method do NOT satisfy HealthCheck
- HealthCheck is runtime_checkable
"""
from __future__ import annotations

import pytest

from openframe.core.health import HealthCheck


# ---------------------------------------------------------------------------
# Helper concrete implementations
# ---------------------------------------------------------------------------


class FullHealthCheck:
    """Implements both required methods."""

    async def ping(self) -> bool:
        return True

    async def is_ready(self) -> bool:
        return True


class MissingIsReady:
    """Has ping() but not is_ready()."""

    async def ping(self) -> bool:
        return True


class MissingPing:
    """Has is_ready() but not ping()."""

    async def is_ready(self) -> bool:
        return True


class EmptyClass:
    """Has neither method."""

    pass


class SyncPing:
    """ping() is sync, not async — should still match at protocol level."""

    def ping(self) -> bool:  # noqa: D102
        return True

    async def is_ready(self) -> bool:
        return True


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_health_check_is_runtime_checkable() -> None:
    # _is_runtime_protocol: Python 3.10/3.11
    # __protocol_attrs__:   Python 3.12+
    assert (
        getattr(HealthCheck, "_is_runtime_protocol", False)
        or hasattr(HealthCheck, "__protocol_attrs__")
    )


def test_full_implementation_satisfies_health_check() -> None:
    adapter = FullHealthCheck()
    assert isinstance(adapter, HealthCheck)


def test_missing_is_ready_fails_health_check() -> None:
    adapter = MissingIsReady()
    assert not isinstance(adapter, HealthCheck)


def test_missing_ping_fails_health_check() -> None:
    adapter = MissingPing()
    assert not isinstance(adapter, HealthCheck)


def test_empty_class_fails_health_check() -> None:
    assert not isinstance(EmptyClass(), HealthCheck)


def test_plain_object_fails_health_check() -> None:
    assert not isinstance(object(), HealthCheck)


async def test_full_health_check_ping_returns_bool() -> None:
    adapter = FullHealthCheck()
    result = await adapter.ping()
    assert result is True


async def test_full_health_check_is_ready_returns_bool() -> None:
    adapter = FullHealthCheck()
    result = await adapter.is_ready()
    assert result is True


def test_sync_ping_satisfies_protocol_structurally() -> None:
    """
    runtime_checkable Protocol checks method *existence*, not coroutine-ness.
    A sync ping() still satisfies isinstance at runtime.
    """
    adapter = SyncPing()
    assert isinstance(adapter, HealthCheck)
