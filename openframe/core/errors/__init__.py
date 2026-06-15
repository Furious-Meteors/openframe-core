"""
openframe.core.errors
======================
Plugin and lifecycle error hierarchy for the OpenFrame platform kernel.

This module is additive — the existing
:mod:`openframe.core.exceptions` module is unchanged.

.. stability: stable
"""
from __future__ import annotations

from openframe.core.errors.plugin import (
    DuplicatePluginError,
    PluginError,
    PluginInitializationError,
    PluginNotFoundError,
)

__all__ = [
    "PluginError",
    "PluginInitializationError",
    "PluginNotFoundError",
    "DuplicatePluginError",
]
