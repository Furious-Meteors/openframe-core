"""
tests/test_exceptions.py
==========================
Tests for openframe.core.exceptions — the unified error hierarchy.

Covers:
- The OpenFrameError root: fields, defaults, catch-all behaviour
- The ErrorCode / Severity taxonomy
- The AdapterError family (backend/infrastructure failures)
- The PluginError family (registry/lifecycle failures)
- Semantics-as-data (code / severity / retryable)
- Constructor back-compat, __str__ output format, cause chaining
"""
from __future__ import annotations

import pytest

from openframe.core.exceptions import (
    AdapterConfigurationError,
    AdapterConnectionError,
    AdapterError,
    AdapterNotFoundError,
    AdapterQueryError,
    AdapterTimeoutError,
    AmbiguousCapabilityError,
    DuplicatePluginError,
    ErrorCode,
    OpenFrameError,
    PluginError,
    PluginInitializationError,
    PluginNotFoundError,
    Severity,
)

# ---------------------------------------------------------------------------
# AdapterError base
# ---------------------------------------------------------------------------


def test_adapter_error_instantiates_without_cause() -> None:
    exc = AdapterError("something failed", "postgres", "get")
    assert exc.message == "something failed"
    assert exc.adapter == "postgres"
    assert exc.operation == "get"
    assert exc.cause is None


def test_adapter_error_instantiates_with_cause() -> None:
    cause = ValueError("underlying error")
    exc = AdapterError("something failed", "redis", "publish", cause=cause)
    assert exc.cause is cause


def test_adapter_error_str_contains_message() -> None:
    exc = AdapterError("entity missing", "postgres", "get")
    assert "entity missing" in str(exc)


def test_adapter_error_str_contains_adapter_and_operation() -> None:
    exc = AdapterError("entity missing", "postgres", "get")
    result = str(exc)
    assert "postgres" in result
    assert "get" in result


def test_adapter_error_str_is_not_tuple_repr() -> None:
    exc = AdapterError("something failed", "postgres", "get")
    result = str(exc)
    # Must not look like a tuple: "('something failed', 'postgres', ...)"
    assert not result.startswith("(")
    assert not result.startswith("'")


def test_adapter_error_str_with_cause_contains_caused_by() -> None:
    cause = RuntimeError("driver exploded")
    exc = AdapterError("query failed", "postgres", "get", cause=cause)
    assert "caused by" in str(exc)


def test_adapter_error_str_without_cause_has_no_caused_by() -> None:
    exc = AdapterError("query failed", "postgres", "get")
    assert "caused by" not in str(exc)


def test_adapter_error_str_format() -> None:
    exc = AdapterError("record not found", "postgres", "get")
    result = str(exc)
    assert result == "[postgres.get] record not found"


def test_adapter_error_str_format_with_cause() -> None:
    cause = ValueError("null constraint")
    exc = AdapterError("insert failed", "postgres", "create", cause=cause)
    result = str(exc)
    assert result.startswith("[postgres.create] insert failed")
    assert "caused by" in result


# ---------------------------------------------------------------------------
# All 5 subclasses: instantiation and isinstance
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "exc_class",
    [
        AdapterConnectionError,
        AdapterQueryError,
        AdapterNotFoundError,
        AdapterConfigurationError,
        AdapterTimeoutError,
    ],
)
def test_subclass_instantiates(exc_class: type[AdapterError]) -> None:
    exc = exc_class("msg", "postgres", "get")
    assert exc.message == "msg"
    assert exc.adapter == "postgres"
    assert exc.operation == "get"
    assert exc.cause is None


@pytest.mark.parametrize(
    "exc_class",
    [
        AdapterConnectionError,
        AdapterQueryError,
        AdapterNotFoundError,
        AdapterConfigurationError,
        AdapterTimeoutError,
    ],
)
def test_subclass_is_adapter_error(exc_class: type[AdapterError]) -> None:
    exc = exc_class("msg", "redis", "publish")
    assert isinstance(exc, AdapterError)


@pytest.mark.parametrize(
    "exc_class",
    [
        AdapterConnectionError,
        AdapterQueryError,
        AdapterNotFoundError,
        AdapterConfigurationError,
        AdapterTimeoutError,
    ],
)
def test_subclass_inherits_str_format(exc_class: type[AdapterError]) -> None:
    exc = exc_class("something bad", "kafka", "consume")
    result = str(exc)
    assert "kafka" in result
    assert "consume" in result
    assert "something bad" in result
    assert not result.startswith("(")


# ---------------------------------------------------------------------------
# Specific subclass behaviour
# ---------------------------------------------------------------------------


def test_adapter_not_found_error_with_cause() -> None:
    cause = KeyError("abc-123")
    exc = AdapterNotFoundError(
        "Item abc-123 not found",
        adapter="postgres",
        operation="get",
        cause=cause,
    )
    assert isinstance(exc, AdapterError)
    assert exc.cause is cause
    assert "caused by" in str(exc)


def test_adapter_configuration_error_no_cause() -> None:
    exc = AdapterConfigurationError(
        "DATABASE_URL must be set",
        adapter="postgres",
        operation="init",
    )
    assert isinstance(exc, AdapterError)
    assert exc.cause is None


def test_adapter_timeout_error_cause_chain() -> None:
    import asyncio

    cause = asyncio.TimeoutError()
    exc = AdapterTimeoutError(
        "Query exceeded 10s timeout",
        adapter="postgres",
        operation="get",
        cause=cause,
    )
    assert exc.cause is cause
    assert "caused by" in str(exc)


# ---------------------------------------------------------------------------
# Exception is raise-able and catch-able
# ---------------------------------------------------------------------------


def test_adapter_error_is_an_exception() -> None:
    with pytest.raises(AdapterError):
        raise AdapterError("test", "postgres", "get")


def test_subclass_caught_as_adapter_error() -> None:
    with pytest.raises(AdapterError):
        raise AdapterQueryError("query failed", "postgres", "list")


def test_cause_chaining_pattern() -> None:
    """Verify the standard raise ... from exc pattern works."""
    original = ValueError("driver error")
    with pytest.raises(AdapterConnectionError) as exc_info:
        try:
            raise original
        except ValueError as exc:
            raise AdapterConnectionError(
                "Cannot connect",
                adapter="postgres",
                operation="connect",
                cause=exc,
            ) from exc
    assert exc_info.value.__cause__ is original
    assert exc_info.value.cause is original


# ---------------------------------------------------------------------------
# OpenFrameError root
# ---------------------------------------------------------------------------


def test_openframe_error_instantiates_with_defaults() -> None:
    exc = OpenFrameError("generic failure")
    assert exc.message == "generic failure"
    assert exc.code == ErrorCode.OPENFRAME
    assert exc.severity is Severity.ERROR
    assert exc.retryable is False
    assert exc.correlation_id is None
    assert exc.context == {}
    assert exc.cause is None


def test_openframe_error_str_is_message() -> None:
    assert str(OpenFrameError("boom")) == "boom"


def test_openframe_error_is_an_exception() -> None:
    assert isinstance(OpenFrameError("x"), Exception)


def test_openframe_error_accepts_per_instance_overrides() -> None:
    cause = ValueError("root")
    exc = OpenFrameError(
        "custom",
        code="ai.rate_limited",
        severity=Severity.WARNING,
        retryable=True,
        correlation_id="abc123",
        context={"provider": "anthropic"},
        cause=cause,
    )
    assert exc.code == "ai.rate_limited"
    assert exc.severity is Severity.WARNING
    assert exc.retryable is True
    assert exc.correlation_id == "abc123"
    assert exc.context == {"provider": "anthropic"}
    assert exc.cause is cause


def test_openframe_error_code_is_plain_str() -> None:
    """code must serialise as a plain string, not 'ErrorCode.X'."""
    exc = AdapterConnectionError("x", adapter="pg", operation="connect")
    assert str(exc.code) == "adapter.connection"
    assert isinstance(exc.code, str)


def test_openframe_error_context_is_mutable_for_enrichment() -> None:
    """Upper-layer seams enrich context/correlation_id on the way up."""
    exc = OpenFrameError("x")
    exc.correlation_id = "trace-1"
    exc.context["extra"] = "value"
    assert exc.correlation_id == "trace-1"
    assert exc.context["extra"] == "value"


# ---------------------------------------------------------------------------
# Catch-all: every family is catchable as OpenFrameError
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "exc",
    [
        AdapterError("m", "pg", "get"),
        AdapterConnectionError("m", "pg", "connect"),
        AdapterNotFoundError("m", "pg", "get"),
        PluginError("m", "p1"),
        DuplicatePluginError("m", "p1"),
        AmbiguousCapabilityError("m", "p1", "persistence", ["p1", "p2"]),
    ],
)
def test_every_family_is_catchable_as_openframe_error(exc: OpenFrameError) -> None:
    assert isinstance(exc, OpenFrameError)


def test_adapter_error_caught_as_openframe_error() -> None:
    with pytest.raises(OpenFrameError):
        raise AdapterQueryError("q", "pg", "list")


def test_plugin_error_caught_as_openframe_error() -> None:
    with pytest.raises(OpenFrameError):
        raise DuplicatePluginError("dup", plugin_name="p1")


# ---------------------------------------------------------------------------
# Adapter family semantics (code / retryable)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("exc_class", "expected_code", "expected_retryable"),
    [
        (AdapterError, ErrorCode.ADAPTER, False),
        (AdapterConnectionError, ErrorCode.ADAPTER_CONNECTION, True),
        (AdapterQueryError, ErrorCode.ADAPTER_QUERY, False),
        (AdapterNotFoundError, ErrorCode.ADAPTER_NOT_FOUND, False),
        (AdapterConfigurationError, ErrorCode.ADAPTER_CONFIGURATION, False),
        (AdapterTimeoutError, ErrorCode.ADAPTER_TIMEOUT, True),
    ],
)
def test_adapter_family_code_and_retryable(
    exc_class: type[AdapterError],
    expected_code: str,
    expected_retryable: bool,
) -> None:
    exc = exc_class("m", "pg", "op")
    assert exc.code == expected_code
    assert exc.retryable is expected_retryable


def test_adapter_error_records_adapter_and_operation_in_context() -> None:
    exc = AdapterError("m", adapter="postgres", operation="get")
    assert exc.context["adapter"] == "postgres"
    assert exc.context["operation"] == "get"


# ---------------------------------------------------------------------------
# Plugin family semantics
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("exc_class", "expected_code"),
    [
        (PluginError, ErrorCode.PLUGIN),
        (PluginInitializationError, ErrorCode.PLUGIN_INITIALIZATION),
        (PluginNotFoundError, ErrorCode.PLUGIN_NOT_FOUND),
        (DuplicatePluginError, ErrorCode.PLUGIN_DUPLICATE),
    ],
)
def test_plugin_family_codes(exc_class: type[PluginError], expected_code: str) -> None:
    exc = exc_class("m", plugin_name="p1")
    assert exc.code == expected_code
    assert exc.plugin_name == "p1"


def test_ambiguous_capability_error_preserves_extra_attributes() -> None:
    exc = AmbiguousCapabilityError(
        "ambiguous",
        plugin_name="pg-main",
        capability="persistence",
        matches=["pg-main", "pg-replica"],
    )
    assert exc.code == ErrorCode.CAPABILITY_AMBIGUOUS
    assert exc.plugin_name == "pg-main"
    assert exc.capability == "persistence"
    assert exc.matches == ["pg-main", "pg-replica"]
    assert isinstance(exc, PluginError)


# ---------------------------------------------------------------------------
# Taxonomy
# ---------------------------------------------------------------------------


def test_error_code_values_follow_domain_kind_convention() -> None:
    for member in ErrorCode:
        assert "." in member.value
        assert member.value == member.value.lower()


def test_severity_values_are_plain_strings() -> None:
    assert str(Severity.WARNING) == "warning"
    assert str(Severity.ERROR) == "error"
    assert str(Severity.CRITICAL) == "critical"
