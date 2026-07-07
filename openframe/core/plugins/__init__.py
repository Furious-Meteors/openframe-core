"""
openframe.core.plugins
=======================
Lightweight plugin kernel for the OpenFrame platform (ADR-006).

A "plugin" is just a registered
:class:`~openframe.core.contracts.port.BasePort` — there is no separate
plugin protocol. This package re-exports the ``contracts`` types
:class:`~openframe.core.plugins.registry.PluginRegistry` operates on for
convenience, plus the registry itself.

All symbols are **experimental** in v3.0 and will stabilise based on real
usage.

.. stability: experimental
"""
from __future__ import annotations

from openframe.core.contracts import (
    BasePort,
    Capability,
    PluginContext,
    PluginHealth,
    PluginStatus,
)
from openframe.core.plugins.registry import PluginRegistry

__all__ = [
    "BasePort",
    "Capability",
    "PluginContext",
    "PluginHealth",
    "PluginStatus",
    "PluginRegistry",
]
