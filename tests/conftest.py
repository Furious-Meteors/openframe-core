"""
tests/conftest.py
==================
Shared pytest fixtures for openframe-core tests.

Four OTel test-isolation concerns are addressed here:

1. ``_INITIALISED`` guard — ``setup_telemetry()`` is idempotent via a
   module-level bool. Without resetting it, the first test that calls
   ``setup_telemetry()`` permanently fixes the telemetry config for all
   subsequent tests in the process.

2. ``get_tracer()`` lru_cache — once populated, ``get_tracer()`` returns
   the same ``Tracer`` object regardless of which ``TracerProvider`` is
   currently set.

3. ``get_meter()`` lru_cache — same issue for meters.

4. OTel SDK "set-once" guards — the most critical issue.
   ``trace.set_tracer_provider()`` and ``metrics.set_meter_provider()``
   are protected by a ``Once`` guard inside the OTel API. The first call
   per process succeeds; ALL subsequent calls are silently rejected with a
   warning::

       WARNING opentelemetry.trace:__init__.py Overriding of current
               TracerProvider is not allowed

   Without resetting these guards, every test after the first sends spans
   to the FIRST test's ``InMemorySpanExporter`` — and all ``span_exporter``
   fixtures from test 2 onwards receive nothing.

   We reset ``_TRACER_PROVIDER_SET_ONCE._done`` and ``_TRACER_PROVIDER``
   directly in the OTel API internals. This is test-infrastructure-only
   access of private state — the alternative is running every test in a
   subprocess.
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


def _reset_otel_globals() -> None:
    """
    Reset the OTel SDK global provider state so ``set_tracer_provider()``
    and ``set_meter_provider()`` succeed in every test.

    The OTel API uses a ``Once`` object (``_TRACER_PROVIDER_SET_ONCE``) that
    sets ``_done = True`` on first use and rejects all subsequent calls.
    Resetting ``_done = False`` and clearing the stored provider reference
    allows the fixture to install a fresh provider per test.
    """
    # Trace
    if hasattr(_otel_trace_api, "_TRACER_PROVIDER_SET_ONCE"):
        _otel_trace_api._TRACER_PROVIDER_SET_ONCE._done = False
    _otel_trace_api._TRACER_PROVIDER = None

    # Metrics (lives in opentelemetry.metrics._internal, not the top-level module)
    if hasattr(_otel_metrics_internal, "_METER_PROVIDER_SET_ONCE"):
        _otel_metrics_internal._METER_PROVIDER_SET_ONCE._done = False
    _otel_metrics_internal._METER_PROVIDER = None


@pytest.fixture(autouse=True)
def reset_telemetry_state():
    """
    Reset ALL telemetry state before and after every test.

    Resets (in order):
    1. openframe ``_INITIALISED`` guard and ``lru_cache`` entries.
    2. OTel SDK ``set_tracer_provider`` / ``set_meter_provider`` once-guards
       so fixture providers are accepted on every test, not just the first.
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
    OTel once-guard, so ``set_tracer_provider`` is accepted. The ``lru_cache``
    is also cleared, so the first ``get_tracer()`` call in the test binds to
    this fixture's provider.

    Does NOT set a ``MeterProvider``. Use ``metric_reader`` for metric
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
