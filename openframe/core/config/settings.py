"""
openframe/core/config/settings.py
====================================
Base settings class for all OpenFrame adapter packages.

Every adapter config (e.g. ``PostgresSettings``, ``RedisSettings``) must
subclass ``BaseAdapterSettings`` and declare its adapter-specific fields.
Pydantic Settings reads field values from environment variables automatically
— the field name maps directly to the env var name (case-insensitive).

Missing required fields raise ``pydantic_core.ValidationError`` at
instantiation time, not at first use. This means misconfigured deployments
fail fast on startup rather than at the first request.

Dependency order: this module imports only from pydantic-settings (external).
No openframe.core imports.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["BaseAdapterSettings"]


class BaseAdapterSettings(BaseSettings):
    """
    Base settings for all OpenFrame adapter packages.

    Subclass in each adapter's ``config/settings.py`` and declare
    adapter-specific fields. All fields are read from environment variables
    automatically by Pydantic Settings.

    Configuration:
        - ``env_prefix = ""`` — field names map directly to env var names.
        - ``case_sensitive = False`` — ``DATABASE_URL`` maps to ``database_url``.
        - ``extra = "ignore"`` — unknown env vars are silently ignored.

    Example::

        class PostgresSettings(BaseAdapterSettings):
            database_url: str          # reads DATABASE_URL — required
            pool_size: int = 10        # reads POOL_SIZE — optional, default 10
            pool_max_overflow: int = 5 # reads POOL_MAX_OVERFLOW

        # Missing DATABASE_URL raises ValidationError immediately:
        settings = PostgresSettings()

    Common fields available on every adapter settings instance:

    Attributes:
        adapter_name:        Identifies the adapter in logs and traces.
                             Reads ``ADAPTER_NAME`` env var.
        connection_timeout:  Seconds to wait when establishing a connection.
                             Reads ``CONNECTION_TIMEOUT``. Default: 30.0.
        operation_timeout:   Seconds to wait for a single operation to complete.
                             Reads ``OPERATION_TIMEOUT``. Default: 10.0.
        max_retries:         Maximum number of retry attempts on transient failure.
                             Reads ``MAX_RETRIES``. Default: 3.
    """

    model_config = SettingsConfigDict(
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    adapter_name: str = "openframe"
    connection_timeout: float = 30.0
    operation_timeout: float = 10.0
    max_retries: int = 3
