"""
openframe.core.plugins
=======================
Lightweight plugin kernel for the OpenFrame platform.

All symbols are **experimental** in v2.0 and will stabilise in v2.1 or v3.0
based on real usage.

.. stability: experimental
"""
from __future__ import annotations

from openframe.core.plugins.contracts import (
    OpenFramePlugin,
    PluginContext,
    PluginHealth,
    PluginStatus,
)
from openframe.core.plugins.registry import PluginRegistry

__all__ = [
    "OpenFramePlugin",
    "PluginContext",
    "PluginHealth",
    "PluginStatus",
    "PluginRegistry",
]
