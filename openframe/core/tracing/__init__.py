"""
openframe/core/tracing/
========================
Generic async telemetry sidecar for the OpenFrame ecosystem.

``TracingProxy`` wraps any adapter object and adds automatic OTel span
instrumentation to every async method, without requiring the adapter or
service layer to know telemetry exists.

Usage::

    from openframe.core.tracing import TracingProxy

    raw_repo = PostgresRepository(settings)
    traced_repo = TracingProxy(raw_repo, prefix="repository.item")

    # Spans named "repository.item.get", "repository.item.create", etc.
    entity = await traced_repo.get(entity_id)
"""
from __future__ import annotations

from openframe.core.tracing.proxy import TracingProxy

__all__ = ["TracingProxy"]
