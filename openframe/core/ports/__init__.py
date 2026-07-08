"""
openframe/core/ports/
=======================
The complete port contract layer for the OpenFrame ecosystem —
the outbound (driven) side of the hexagon.

Unified in v3.1.0 from two formerly separate modules:
  - ``openframe.core.contracts`` — port primitives (Identity, Lifecycle,
    BasePort, Capability, PluginStatus, PluginHealth, PluginContext,
    PrincipalContext, TenantContext). Now lives here.
  - ``openframe.core.ports`` — capability-specific outbound port
    protocols (BaseRepository, BaseProducer, BaseConsumer). Moved into
    the ``outbound/`` sub-module.

See ``docs/technical/architecture/adrs/adr-006-unified-port-lifecycle.md``
for the full design rationale. No compatibility shim is provided at the
old ``openframe.core.contracts`` path — update all imports to
``openframe.core.ports``.

**Port primitives** — the building blocks every port is made of::

    from openframe.core.ports import (
        BasePort, Capability, Identity, Lifecycle,
        PluginStatus, PluginHealth, PluginContext,
        PrincipalContext, TenantContext,
    )

**Outbound port protocols** — capability-specific protocols built on
top of BasePort, defined in ``ports/outbound/`` (see that sub-module's
docstring for the intake rule on future capabilities)::

    from openframe.core.ports import BaseRepository, BaseProducer, BaseConsumer

Runtime isinstance checks::

    isinstance(repo, BaseRepository)        # works
    isinstance(repo, BaseRepository[str])   # raises TypeError — unparameterised only
"""
from __future__ import annotations

from openframe.core.ports.capability import Capability
from openframe.core.ports.context import PrincipalContext, TenantContext
from openframe.core.ports.health import PluginContext, PluginHealth, PluginStatus
from openframe.core.ports.identity import Identity
from openframe.core.ports.lifecycle import Lifecycle
from openframe.core.ports.outbound import BaseConsumer, BaseProducer, BaseRepository
from openframe.core.ports.port import BasePort

__all__ = [
    # Port primitives
    "Identity",
    "Lifecycle",
    "BasePort",
    "Capability",
    "PluginStatus",
    "PluginHealth",
    "PluginContext",
    "PrincipalContext",
    "TenantContext",
    # Outbound port protocols
    "BaseRepository",
    "BaseProducer",
    "BaseConsumer",
]
