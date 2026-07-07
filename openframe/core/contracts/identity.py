"""
openframe/core/contracts/identity.py
======================================
Identity half of the unified BasePort contract (ADR-006).

``Identity`` is the "what is this thing" side — a name, a version, and a
typed capability. Combined with :class:`~openframe.core.contracts.lifecycle.Lifecycle`
(the "how is this thing managed" side) it forms
:class:`~openframe.core.contracts.port.BasePort`.

Dependency order:
    contracts/capability → (no openframe imports)
    contracts/identity   → contracts/capability
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from openframe.core.contracts.capability import Capability

__all__ = ["Identity"]


@runtime_checkable
class Identity(Protocol):
    """
    Identity contract — every registrable port/plugin declares who it is.

    Adapters satisfy this protocol structurally — no inheritance needed.
    Any class with matching ``name``/``version``/``capability`` attributes
    satisfies ``Identity``.

    Attributes:
        name:       Unique instance name within a
                    :class:`~openframe.core.plugins.registry.PluginRegistry`
                    (e.g. ``"postgres-main"``).
        version:    Semantic version string of the adapter implementation
                    (e.g. ``"1.2.3"``) — not the protocol version.
        capability: Logical role from the closed
                    :class:`~openframe.core.contracts.capability.Capability`
                    taxonomy. Used for capability-based lookup via
                    :meth:`~openframe.core.plugins.registry.PluginRegistry.get`.
    """

    name: str
    version: str
    capability: Capability
