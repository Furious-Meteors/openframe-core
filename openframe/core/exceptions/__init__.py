"""
openframe/core/exceptions/
============================
Structured exception hierarchy for all OpenFrame adapter packages.

All adapter packages raise only these exceptions — never raw driver
exceptions. Services catch ``AdapterError`` as a single catch point
regardless of which adapter is wired in.

Usage::

    from openframe.core.exceptions import (
        AdapterError,
        AdapterConnectionError,
        AdapterQueryError,
        AdapterNotFoundError,
        AdapterConfigurationError,
        AdapterTimeoutError,
    )
"""
from __future__ import annotations

from openframe.core.exceptions.errors import (
    AdapterConfigurationError,
    AdapterConnectionError,
    AdapterError,
    AdapterNotFoundError,
    AdapterQueryError,
    AdapterTimeoutError,
)

__all__ = [
    "AdapterError",
    "AdapterConnectionError",
    "AdapterQueryError",
    "AdapterNotFoundError",
    "AdapterConfigurationError",
    "AdapterTimeoutError",
]
