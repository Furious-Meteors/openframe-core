"""
openframe/core/exceptions/
============================
Unified exception hierarchy for the entire OpenFrame ecosystem.

Single root
-----------
``OpenFrameError`` is the root of every error the ecosystem raises. Both the
adapter family (backend/infrastructure failures) and the plugin family
(registry/lifecycle failures) derive from it, so a single
``except OpenFrameError`` is a catch point for the whole platform.

Adapter packages still raise only ``AdapterError`` subclasses — never raw
driver exceptions.

Usage::

    from openframe.core.exceptions import (
        OpenFrameError,          # catch-all root
        ErrorCode, Severity,     # typed taxonomy
        AdapterError,            # backend/infrastructure family
        AdapterConnectionError,
        AdapterQueryError,
        AdapterNotFoundError,
        AdapterConfigurationError,
        AdapterTimeoutError,
        PluginError,             # registry/lifecycle family
        PluginInitializationError,
        PluginNotFoundError,
        DuplicatePluginError,
        AmbiguousCapabilityError,
    )
"""
from __future__ import annotations

from openframe.core.exceptions.adapter import (
    AdapterConfigurationError,
    AdapterConnectionError,
    AdapterError,
    AdapterNotFoundError,
    AdapterQueryError,
    AdapterTimeoutError,
)
from openframe.core.exceptions.base import OpenFrameError
from openframe.core.exceptions.codes import ErrorCode, Severity
from openframe.core.exceptions.plugin import (
    AmbiguousCapabilityError,
    DuplicatePluginError,
    PluginError,
    PluginInitializationError,
    PluginNotFoundError,
)

__all__ = [
    # Root + taxonomy
    "OpenFrameError",
    "ErrorCode",
    "Severity",
    # Adapter family
    "AdapterError",
    "AdapterConnectionError",
    "AdapterQueryError",
    "AdapterNotFoundError",
    "AdapterConfigurationError",
    "AdapterTimeoutError",
    # Plugin family
    "PluginError",
    "PluginInitializationError",
    "PluginNotFoundError",
    "DuplicatePluginError",
    "AmbiguousCapabilityError",
]
