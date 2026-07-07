"""
tests/test_shutdown_telemetry.py
==================================
Tests for ``openframe.core.telemetry.shutdown_telemetry`` and the
``ApplicationBootstrap.stop()`` integration.

Covers:
- shutdown_telemetry() calls shutdown() on TracerProvider and MeterProvider
- shutdown_telemetry() clears _tracer_provider and _meter_provider references
- shutdown_telemetry() resets _INITIALISED so setup_telemetry() can re-run
- shutdown_telemetry() clears lru_cache entries for get_tracer / get_meter
- shutdown_telemetry() is idempotent (safe to call when not initialised)
- shutdown_telemetry() is idempotent (safe to call twice)
- ApplicationBootstrap.stop() calls shutdown_telemetry()
"""
from __future__ import annotations

import pytest

import openframe.core.telemetry.setup as telemetry_setup
from openframe.core.telemetry import setup_telemetry, shutdown_telemetry


# ---------------------------------------------------------------------------
# shutdown_telemetry() unit tests
# ---------------------------------------------------------------------------


def test_shutdown_resets_initialised_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """After shutdown, _INITIALISED is False so setup_telemetry() can re-run."""
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.setenv("OPENFRAME_TELEMETRY_DISABLED", "1")

    setup_telemetry()
    assert telemetry_setup._INITIALISED is True

    shutdown_telemetry()
    assert telemetry_setup._INITIALISED is False


def test_shutdown_clears_provider_references(monkeypatch: pytest.MonkeyPatch) -> None:
    """After shutdown, the module-level provider references are None."""
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.setenv("OPENFRAME_TELEMETRY_DISABLED", "1")

    setup_telemetry()
    assert telemetry_setup._tracer_provider is not None
    assert telemetry_setup._meter_provider is not None

    shutdown_telemetry()
    assert telemetry_setup._tracer_provider is None
    assert telemetry_setup._meter_provider is None


def test_shutdown_clears_lru_caches(monkeypatch: pytest.MonkeyPatch) -> None:
    """After shutdown, get_tracer and get_meter lru_cache entries are gone."""
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.setenv("OPENFRAME_TELEMETRY_DISABLED", "1")

    setup_telemetry()
    telemetry_setup.get_tracer("seed-entry")
    telemetry_setup.get_meter("seed-entry")
    assert telemetry_setup.get_tracer.cache_info().currsize > 0
    assert telemetry_setup.get_meter.cache_info().currsize > 0

    shutdown_telemetry()
    assert telemetry_setup.get_tracer.cache_info().currsize == 0
    assert telemetry_setup.get_meter.cache_info().currsize == 0


def test_shutdown_allows_reinitialisation(monkeypatch: pytest.MonkeyPatch) -> None:
    """setup_telemetry() can run again after shutdown_telemetry()."""
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.setenv("OPENFRAME_TELEMETRY_DISABLED", "1")

    setup_telemetry()
    assert telemetry_setup._INITIALISED is True

    shutdown_telemetry()
    assert telemetry_setup._INITIALISED is False

    # Should not raise, and should set _INITIALISED again.
    setup_telemetry()
    assert telemetry_setup._INITIALISED is True


def test_shutdown_idempotent_when_never_initialised() -> None:
    """shutdown_telemetry() is safe to call before setup_telemetry() ever runs."""
    assert telemetry_setup._INITIALISED is False
    shutdown_telemetry()  # must not raise
    assert telemetry_setup._INITIALISED is False


def test_shutdown_idempotent_when_called_twice(monkeypatch: pytest.MonkeyPatch) -> None:
    """Calling shutdown_telemetry() twice does not raise."""
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.setenv("OPENFRAME_TELEMETRY_DISABLED", "1")

    setup_telemetry()
    shutdown_telemetry()
    shutdown_telemetry()  # must not raise


# ---------------------------------------------------------------------------
# ApplicationBootstrap.stop() integration
# ---------------------------------------------------------------------------


async def test_bootstrap_stop_calls_shutdown_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ApplicationBootstrap.stop() flushes telemetry after shutting down ports."""
    from openframe.core.runtime import ApplicationBootstrap

    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.setenv("OPENFRAME_TELEMETRY_DISABLED", "1")

    setup_telemetry()
    assert telemetry_setup._INITIALISED is True

    bootstrap = ApplicationBootstrap()
    await bootstrap.stop()

    # stop() must have called shutdown_telemetry(), which resets _INITIALISED.
    assert telemetry_setup._INITIALISED is False
    assert telemetry_setup._tracer_provider is None
    assert telemetry_setup._meter_provider is None


async def test_bootstrap_context_manager_stop_calls_shutdown_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ApplicationBootstrap used as async context manager also shuts down telemetry."""
    from openframe.core.runtime import ApplicationBootstrap

    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.setenv("OPENFRAME_TELEMETRY_DISABLED", "1")

    setup_telemetry()

    async with ApplicationBootstrap():
        assert telemetry_setup._INITIALISED is True

    assert telemetry_setup._INITIALISED is False
