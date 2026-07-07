"""
openframe/core/exceptions/plugin.py
=====================================
Plugin lifecycle / registry orchestration exception family.

Raised by :class:`~openframe.core.plugins.registry.PluginRegistry` during
plugin registration and lifecycle management. These represent internal
orchestration failures (a name collided, a lookup was ambiguous, a plugin
was not found) — distinct from :class:`~openframe.core.exceptions.adapter.AdapterError`,
which represents a backend/infrastructure operation failure.

All classes here derive from
:class:`~openframe.core.exceptions.base.OpenFrameError`, so a plugin error
is also catchable as ``OpenFrameError``.

Dependency order: imports ``openframe.core.exceptions.base`` + ``.codes`` only.

.. stability: stable
"""
from __future__ import annotations

from openframe.core.exceptions.base import OpenFrameError
from openframe.core.exceptions.codes import ErrorCode

__all__ = [
    "PluginError",
    "PluginInitializationError",
    "PluginNotFoundError",
    "DuplicatePluginError",
    "AmbiguousCapabilityError",
]

__stability__ = "stable"


class PluginError(OpenFrameError):
    """
    Base exception for plugin lifecycle errors.

    All plugin-related exceptions raised by
    :class:`~openframe.core.plugins.registry.PluginRegistry` derive from
    this class, allowing callers to catch all plugin errors at a single point
    (or, more broadly, as :class:`~openframe.core.exceptions.base.OpenFrameError`).

    Attributes:
        message:     Human-readable description of the error.
        plugin_name: The name of the plugin that caused the error.
    """

    code = ErrorCode.PLUGIN

    def __init__(self, message: str, plugin_name: str) -> None:
        """
        Initialise the plugin error.

        Args:
            message:     Human-readable description of the failure.
            plugin_name: Name of the plugin involved.
        """
        super().__init__(message, context={"plugin_name": plugin_name})
        self.plugin_name = plugin_name

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            f"message={self.message!r}, "
            f"plugin_name={self.plugin_name!r})"
        )


class PluginInitializationError(PluginError):
    """
    Raised when a plugin fails to initialize.

    Wraps the underlying exception from ``plugin.initialize()``.
    The registry re-raises this after rolling back already-initialized plugins.
    """

    code = ErrorCode.PLUGIN_INITIALIZATION


class PluginNotFoundError(PluginError):
    """
    Raised when a plugin is not found in the registry.

    Distinct from ``KeyError`` — carries ``plugin_name`` context.
    """

    code = ErrorCode.PLUGIN_NOT_FOUND


class DuplicatePluginError(PluginError):
    """
    Raised when a plugin with the same name is registered twice.

    The registry requires each plugin name to be unique within a single
    registry instance. Use distinct names or distinct registry instances
    for multiple plugins of the same type.
    """

    code = ErrorCode.PLUGIN_DUPLICATE


class AmbiguousCapabilityError(PluginError):
    """
    Raised by :meth:`~openframe.core.plugins.registry.PluginRegistry.get`
    when more than one port is registered under the requested capability.

    This is the "strict duplicate-capability guard" from ADR-006:
    ``get()`` never silently returns the first match when the result is
    ambiguous — use
    :meth:`~openframe.core.plugins.registry.PluginRegistry.get_all` when
    multiple ports sharing a capability (e.g. a primary + replica
    persistence pair) is the intended configuration.

    Attributes:
        capability: The capability that matched more than one port.
        matches:    Names of all ports registered under that capability.
    """

    code = ErrorCode.CAPABILITY_AMBIGUOUS

    def __init__(
        self,
        message: str,
        plugin_name: str,
        capability: object,
        matches: list[str],
    ) -> None:
        """
        Initialise the error.

        Args:
            message:     Human-readable description of the ambiguity.
            plugin_name: Name of the first matching port (for base-class
                         compatibility with ``PluginError``).
            capability:  The capability that matched more than one port.
            matches:     Names of all ports registered under that capability.
        """
        super().__init__(message, plugin_name)
        self.capability = capability
        self.matches = matches
