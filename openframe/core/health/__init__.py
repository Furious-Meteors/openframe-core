"""
openframe/core/health/
=======================
Health check port for all OpenFrame adapter packages.

Every adapter implements ``HealthCheck`` so the application layer can
verify liveness and readiness without knowing which adapter is wired in.

Usage::

    from openframe.core.health import HealthCheck

    assert isinstance(my_adapter, HealthCheck)
"""
from __future__ import annotations

from openframe.core.health.protocol import HealthCheck

__all__ = ["HealthCheck"]
