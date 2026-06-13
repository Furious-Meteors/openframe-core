"""
tests/test_config.py
======================
Tests for openframe.core.config — BaseAdapterSettings.

Covers:
- Default field values
- Reading fields from environment variables
- Subclass with required field raises ValidationError when env var absent
- Subclass with required field reads from env correctly
- Subclass with optional int field coerces from env string
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from openframe.core.config import BaseAdapterSettings


# ---------------------------------------------------------------------------
# Default values
# ---------------------------------------------------------------------------


def test_base_adapter_settings_defaults() -> None:
    settings = BaseAdapterSettings()
    assert settings.adapter_name == "openframe"
    assert settings.connection_timeout == 30.0
    assert settings.operation_timeout == 10.0
    assert settings.max_retries == 3


def test_connection_timeout_default_is_float() -> None:
    settings = BaseAdapterSettings()
    assert isinstance(settings.connection_timeout, float)
    assert settings.connection_timeout == 30.0


def test_operation_timeout_default_is_float() -> None:
    settings = BaseAdapterSettings()
    assert isinstance(settings.operation_timeout, float)
    assert settings.operation_timeout == 10.0


def test_max_retries_default_is_int() -> None:
    settings = BaseAdapterSettings()
    assert isinstance(settings.max_retries, int)
    assert settings.max_retries == 3


# ---------------------------------------------------------------------------
# Environment variable override of base fields
# ---------------------------------------------------------------------------


def test_connection_timeout_reads_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONNECTION_TIMEOUT", "60.0")
    settings = BaseAdapterSettings()
    assert settings.connection_timeout == 60.0


def test_operation_timeout_reads_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPERATION_TIMEOUT", "5.0")
    settings = BaseAdapterSettings()
    assert settings.operation_timeout == 5.0


def test_max_retries_reads_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAX_RETRIES", "10")
    settings = BaseAdapterSettings()
    assert settings.max_retries == 10


def test_adapter_name_reads_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADAPTER_NAME", "myservice")
    settings = BaseAdapterSettings()
    assert settings.adapter_name == "myservice"


# ---------------------------------------------------------------------------
# Subclass with required field
# ---------------------------------------------------------------------------


def test_subclass_required_field_raises_when_env_absent() -> None:
    class PostgresSettings(BaseAdapterSettings):
        database_url: str

    with pytest.raises(ValidationError):
        PostgresSettings()


def test_subclass_required_field_reads_from_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class PostgresSettings(BaseAdapterSettings):
        database_url: str

    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")
    settings = PostgresSettings()
    assert settings.database_url == "postgresql://localhost/test"


def test_subclass_optional_int_field_reads_from_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class PostgresSettings(BaseAdapterSettings):
        pool_size: int = 10

    monkeypatch.setenv("POOL_SIZE", "20")
    settings = PostgresSettings()
    assert settings.pool_size == 20
    assert isinstance(settings.pool_size, int)


def test_subclass_inherits_base_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    class RedisSettings(BaseAdapterSettings):
        redis_url: str

    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379")
    settings = RedisSettings()
    assert settings.connection_timeout == 30.0
    assert settings.operation_timeout == 10.0
    assert settings.max_retries == 3


def test_subclass_extra_env_vars_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    """extra='ignore' means unknown env vars don't raise."""

    class MinimalSettings(BaseAdapterSettings):
        pass

    monkeypatch.setenv("COMPLETELY_UNKNOWN_VAR_XYZ", "some_value")
    settings = MinimalSettings()
    # Should not raise — extra env vars are silently ignored
    assert settings.adapter_name == "openframe"


def test_subclass_case_insensitive_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """case_sensitive=False — lowercase env var name works too."""

    class MySettings(BaseAdapterSettings):
        my_secret: str

    monkeypatch.setenv("my_secret", "hidden")
    settings = MySettings()
    assert settings.my_secret == "hidden"
