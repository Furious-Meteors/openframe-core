"""
openframe.core.contracts
==========================
Unified port + lifecycle contract layer (ADR-006).

The canonical home for every structural primitive shared across the
outbound (``ports``) and inbound (``inbound``) sides of the hexagon:

- :class:`~openframe.core.contracts.identity.Identity` — name/version/capability.
- :class:`~openframe.core.contracts.lifecycle.Lifecycle` — initialize/shutdown/health.
- :class:`~openframe.core.contracts.port.BasePort` — ``Identity + Lifecycle``,
  the single base every outbound port extends.
- :class:`~openframe.core.contracts.capability.Capability` — closed
  capability taxonomy (``PERSISTENCE``, ``CACHE``, ``QUEUE``, ...).
- :class:`~openframe.core.contracts.health.PluginStatus`,
  :class:`~openframe.core.contracts.health.PluginHealth`,
  :class:`~openframe.core.contracts.health.PluginContext` — the canonical
  lifecycle status/health/init-context trio.
- :class:`~openframe.core.contracts.context.PrincipalContext`,
  :class:`~openframe.core.contracts.context.TenantContext` — identity
  primitives threaded through both ``PluginContext`` (outbound) and
  ``RequestContext`` (inbound).

**What belongs here**

A type belongs in ``contracts/`` only if removing it would force two or
more of ``ports/``, ``inbound/``, and ``plugins/`` to either duplicate it
or import from each other. Types needed by only one downstream module
belong in that module, not here.

See ``docs/technical/architecture/adrs/adr-006-unified-port-lifecycle.md``
for the full design rationale, including what this module replaces
(``health/``, ``plugins/contracts.OpenFramePlugin``, the pre-v3
lifecycle-free ``ports/`` protocols).

Usage::

    from openframe.core.contracts import BasePort, Capability, PluginHealth

    assert isinstance(my_adapter, BasePort)
"""
from __future__ import annotations

from openframe.core.contracts.capability import Capability
from openframe.core.contracts.context import PrincipalContext, TenantContext
from openframe.core.contracts.health import PluginContext, PluginHealth, PluginStatus
from openframe.core.contracts.identity import Identity
from openframe.core.contracts.lifecycle import Lifecycle
from openframe.core.contracts.port import BasePort

__all__ = [
    "Identity",
    "Lifecycle",
    "BasePort",
    "Capability",
    "PluginStatus",
    "PluginHealth",
    "PluginContext",
    "PrincipalContext",
    "TenantContext",
]
