"""
tests/test_resilience.py
==========================
Tests for openframe.core.resilience — CircuitBreakerProxy.

Covers:
- Closed → open transition after failure_threshold consecutive failures
- Open state short-circuits immediately (wrapped method never called)
- Open → half-open transition after reset_timeout elapses
- Half-open → closed transition on a successful probe
- Half-open → open transition on a failed probe (timer restarts)
- A single success resets the consecutive-failure counter
- Sync methods pass through unwrapped, uncounted
- Reconnect safety: method resolved fresh on every call
- Constructor validation
"""
from __future__ import annotations

import asyncio

import pytest

from openframe.core.exceptions import AdapterConnectionError
from openframe.core.resilience import CircuitBreakerProxy, CircuitState


# ---------------------------------------------------------------------------
# Helper adapter
# ---------------------------------------------------------------------------


class FlakyAdapter:
    """Adapter whose async method can be scripted to fail or succeed."""

    def __init__(self) -> None:
        self.call_count = 0
        self._should_fail: list[bool] = []

    def script(self, *outcomes: bool) -> None:
        """Queue up outcomes: True = raise, False = succeed."""
        self._should_fail = list(outcomes)

    async def do_work(self) -> str:
        self.call_count += 1
        if self._should_fail:
            should_fail = self._should_fail.pop(0)
            if should_fail:
                raise RuntimeError("backend failure")
        return "ok"

    def sync_method(self) -> str:
        return "sync_result"


# ---------------------------------------------------------------------------
# Constructor validation
# ---------------------------------------------------------------------------


def test_rejects_non_positive_failure_threshold() -> None:
    with pytest.raises(ValueError):
        CircuitBreakerProxy(FlakyAdapter(), failure_threshold=0)


def test_rejects_non_positive_reset_timeout() -> None:
    with pytest.raises(ValueError):
        CircuitBreakerProxy(FlakyAdapter(), reset_timeout=0.0)


def test_starts_closed() -> None:
    proxy = CircuitBreakerProxy(FlakyAdapter())
    assert proxy.state is CircuitState.CLOSED


# ---------------------------------------------------------------------------
# Sync passthrough
# ---------------------------------------------------------------------------


def test_sync_method_passes_through_unwrapped() -> None:
    proxy = CircuitBreakerProxy(FlakyAdapter())
    assert proxy.sync_method() == "sync_result"


# ---------------------------------------------------------------------------
# Closed → Open
# ---------------------------------------------------------------------------


async def test_opens_after_failure_threshold_consecutive_failures() -> None:
    wrapped = FlakyAdapter()
    wrapped.script(True, True, True)
    proxy = CircuitBreakerProxy(wrapped, failure_threshold=3, reset_timeout=30.0)

    for _ in range(3):
        with pytest.raises(RuntimeError):
            await proxy.do_work()

    assert proxy.state is CircuitState.OPEN


async def test_stays_closed_below_failure_threshold() -> None:
    wrapped = FlakyAdapter()
    wrapped.script(True, True)
    proxy = CircuitBreakerProxy(wrapped, failure_threshold=3, reset_timeout=30.0)

    for _ in range(2):
        with pytest.raises(RuntimeError):
            await proxy.do_work()

    assert proxy.state is CircuitState.CLOSED


async def test_success_resets_consecutive_failure_count() -> None:
    """A success between failures must reset the counter — not accumulate."""
    wrapped = FlakyAdapter()
    wrapped.script(True, True, False, True, True)
    proxy = CircuitBreakerProxy(wrapped, failure_threshold=3, reset_timeout=30.0)

    with pytest.raises(RuntimeError):
        await proxy.do_work()
    with pytest.raises(RuntimeError):
        await proxy.do_work()
    await proxy.do_work()  # success — resets the counter
    assert proxy.state is CircuitState.CLOSED

    with pytest.raises(RuntimeError):
        await proxy.do_work()
    with pytest.raises(RuntimeError):
        await proxy.do_work()
    # Only 2 consecutive failures since the reset — must still be closed.
    assert proxy.state is CircuitState.CLOSED


# ---------------------------------------------------------------------------
# Open state — short-circuit behaviour
# ---------------------------------------------------------------------------


async def test_open_circuit_short_circuits_without_calling_wrapped() -> None:
    wrapped = FlakyAdapter()
    wrapped.script(True)
    proxy = CircuitBreakerProxy(wrapped, failure_threshold=1, reset_timeout=30.0, name="my-adapter")

    with pytest.raises(RuntimeError):
        await proxy.do_work()
    assert proxy.state is CircuitState.OPEN

    calls_before = wrapped.call_count
    with pytest.raises(AdapterConnectionError) as exc_info:
        await proxy.do_work()

    # The wrapped method must NOT have been invoked a second time.
    assert wrapped.call_count == calls_before
    assert exc_info.value.retryable is True
    assert exc_info.value.adapter == "my-adapter"
    assert exc_info.value.operation == "do_work"


# ---------------------------------------------------------------------------
# Open → Half-open → Closed / Open
# ---------------------------------------------------------------------------


async def test_half_open_probe_success_closes_circuit() -> None:
    wrapped = FlakyAdapter()
    wrapped.script(True)  # opens the circuit
    proxy = CircuitBreakerProxy(wrapped, failure_threshold=1, reset_timeout=0.05)

    with pytest.raises(RuntimeError):
        await proxy.do_work()
    assert proxy.state is CircuitState.OPEN

    await asyncio.sleep(0.06)  # let reset_timeout elapse
    wrapped.script(False)  # the probe call succeeds
    result = await proxy.do_work()

    assert result == "ok"
    assert proxy.state is CircuitState.CLOSED


async def test_half_open_probe_failure_reopens_circuit() -> None:
    wrapped = FlakyAdapter()
    wrapped.script(True)  # opens the circuit
    proxy = CircuitBreakerProxy(wrapped, failure_threshold=1, reset_timeout=0.05)

    with pytest.raises(RuntimeError):
        await proxy.do_work()
    assert proxy.state is CircuitState.OPEN

    await asyncio.sleep(0.06)  # let reset_timeout elapse
    wrapped.script(True)  # the probe call also fails
    with pytest.raises(RuntimeError):
        await proxy.do_work()

    assert proxy.state is CircuitState.OPEN


async def test_open_before_reset_timeout_elapses_stays_open() -> None:
    wrapped = FlakyAdapter()
    wrapped.script(True)
    proxy = CircuitBreakerProxy(wrapped, failure_threshold=1, reset_timeout=10.0)

    with pytest.raises(RuntimeError):
        await proxy.do_work()
    assert proxy.state is CircuitState.OPEN

    # No sleep — well within reset_timeout=10.0s.
    with pytest.raises(AdapterConnectionError):
        await proxy.do_work()
    assert proxy.state is CircuitState.OPEN


# ---------------------------------------------------------------------------
# Reconnect safety
# ---------------------------------------------------------------------------


async def test_resolves_method_fresh_after_replacement() -> None:
    """
    Like TracingProxy, the wrapped method must be resolved fresh on every
    call — replacing the wrapped object's method after proxy construction
    must be picked up immediately, not a stale snapshot.
    """
    wrapped = FlakyAdapter()
    proxy = CircuitBreakerProxy(wrapped)

    async def replaced(*args: object, **kwargs: object) -> str:
        return "replaced_result"

    wrapped.do_work = replaced  # type: ignore[method-assign]
    result = await proxy.do_work()
    assert result == "replaced_result"
