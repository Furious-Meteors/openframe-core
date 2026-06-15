"""
openframe/core/testing/fixtures.py
=====================================
Canonical pytest fixtures for OpenTelemetry isolation in openframe adapter tests.

Every adapter package imports these fixtures in its ``conftest.py``::

    from openframe.core.testing.fixtures import *  # noqa: F401, F403

This gives every adapter test suite the same OTel reset behaviour without
duplicating the reset logic in each package.

Fixtures provided
-----------------
``reset_telemetry_state`` (autouse)
    Resets all OTel global provider state before *and* after every test.
    Prevents provider contamination — without this, the first test that
    calls ``setup_telemetry()`` permanently fixes the tracer/meter for all
    subsequent tests in the same process.

    Specifically resets:
    - openframe ``_INITIALISED`` guard
    - ``get_tracer`` / ``get_meter`` lru_cache entries
    - OTel SDK ``_TRACER_PROVIDER_SET_ONCE._done`` and ``_TRACER_PROVIDER``
    - OTel SDK ``_METER_PROVIDER_SET_ONCE._done`` and ``_METER_PROVIDER``

``span_exporter`` (on-demand)
    A fresh :class:`~opentelemetry.sdk.trace.export.InMemorySpanExporter`
    wired to the global ``TracerProvider``.  Call
    ``span_exporter.get_finished_spans()`` after the operation under test.

``metric_reader`` (on-demand)
    A fresh :class:`~opentelemetry.sdk.metrics.export.InMemoryMetricReader`
    wired to the global ``MeterProvider``.  Call
    ``metric_reader.get_metrics_data()`` after the operation under test.

.. stability: stable
"""
from __future__ import annotations

import opentelemetry.metrics._internal as _otel_metrics_internal
import opentelemetry.trace as _otel_trace_api
import pytest
from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

import openframe.core.telemetry.setup as _telemetry

__all__ = [
    "reset_telemetry_state",
    "span_exporter",
    "metric_reader",
]

__stability__ = "stable"


def _reset_otel_globals() -> None:
    """
    Reset the OTel SDK global provider state so ``set_tracer_provider()``
    and ``set_meter_provider()`` succeed in every test.

    The OTel API uses a ``Once`` object that sets ``_done = True`` on first
    use and rejects all subsequent calls.  Resetting ``_done = False`` and
    clearing the stored provider reference allows each test to install a
    fresh provider.
    """
    if hasattr(_otel_trace_api, "_TRACER_PROVIDER_SET_ONCE"):
        _otel_trace_api._TRACER_PROVIDER_SET_ONCE._done = False
    _otel_trace_api._TRACER_PROVIDER = None

    if hasattr(_otel_metrics_internal, "_METER_PROVIDER_SET_ONCE"):
        _otel_metrics_internal._METER_PROVIDER_SET_ONCE._done = False
    _otel_metrics_internal._METER_PROVIDER = None


@pytest.fixture(autouse=True)
def reset_telemetry_state():
    """
    Reset ALL telemetry state before and after every test (autouse).

    Resets (in order):

    1. openframe ``_INITIALISED`` guard and ``lru_cache`` entries.
    2. OTel SDK ``set_tracer_provider`` / ``set_meter_provider`` once-guards
       so fixture providers are accepted on every test, not just the first.

    This fixture is ``autouse=True`` — it runs for every test in any
    conftest that imports it, without requiring explicit fixture parameters.
    """
    _telemetry._INITIALISED = False
    _telemetry.get_tracer.cache_clear()
    _telemetry.get_meter.cache_clear()
    _reset_otel_globals()
    yield
    _telemetry._INITIALISED = False
    _telemetry.get_tracer.cache_clear()
    _telemetry.get_meter.cache_clear()
    _reset_otel_globals()


@pytest.fixture
def span_exporter() -> InMemorySpanExporter:
    """
    Provide a fresh ``InMemorySpanExporter`` wired to the global ``TracerProvider``.

    The ``reset_telemetry_state`` autouse fixture runs first and resets the
    OTel once-guard, so ``set_tracer_provider`` is accepted.  The
    ``lru_cache`` is also cleared, so the first ``get_tracer()`` call in
    the test binds to this fixture's provider.

    Does NOT set a ``MeterProvider``.  Use ``metric_reader`` for metric
    assertions, or combine both fixtures when a test needs both.

    Yields:
        ``InMemorySpanExporter`` — call ``.get_finished_spans()`` to inspect.
    """
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    yield exporter
    exporter.clear()


@pytest.fixture
def metric_reader() -> InMemoryMetricReader:
    """
    Provide a fresh ``InMemoryMetricReader`` wired to the global ``MeterProvider``.

    Can be combined with ``span_exporter`` — both providers are accepted
    because ``reset_telemetry_state`` resets the OTel once-guards before
    any fixture runs.

    Call ``metric_reader.get_metrics_data()`` after the operation under test.

    Yields:
        ``InMemoryMetricReader`` — call ``.get_metrics_data()`` to inspect.
    """
    reader = InMemoryMetricReader()
    provider = MeterProvider(metric_readers=[reader])
    metrics.set_meter_provider(provider)
    yield reader
