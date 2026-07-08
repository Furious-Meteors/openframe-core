"""
openframe.core.runtime
=======================
Recommended composition root for OpenFrame applications.

``ApplicationBootstrap`` is the recommended starting point for wiring ports
in application code. It wraps ``PluginRegistry``, adds a structured
``configure → start → stop`` lifecycle, and ensures telemetry is flushed on
shutdown via ``shutdown_telemetry()``.

See ``openframe.core.plugins.PluginRegistry`` if you need fine-grained
control over initialization order or want to manage the registry lifecycle
directly without the composition abstraction.

.. stability: experimental
"""
from __future__ import annotations

from openframe.core.runtime.bootstrap import ApplicationBootstrap

__all__ = ["ApplicationBootstrap"]
