"""
tests/test_exceptions.py
==========================
Tests for openframe.core.exceptions — the AdapterError hierarchy.

Covers:
- All 6 classes instantiate correctly
- All 5 subclasses are subclasses of AdapterError
- __str__ output format (not a tuple repr)
- All four instance attributes are accessible
- Cause chaining behaviour
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
