"""
openframe/core/errors/plugin.py
================================
Plugin lifecycle error hierarchy for the OpenFrame platform kernel.

Raised by :class:`~openframe.core.plugins.registry.PluginRegistry` during
plugin registration and lifecycle management.

Dependency order: no openframe.core imports.

.. stability: stable
   Stable — no breaking changes until v3.0.
"""
from __future__ import annotations

__all__ = [
    "PluginError",
    "PluginInitializationError",
    "PluginNotFoundError",
    "DuplicatePluginError",
]

__stability__ = "stable"


class PluginError(Exception):
    """
    Base exception for plugin lifecycle errors.

    All plugin-related exceptions raised by
    :class:`~openframe.core.plugins.registry.PluginRegistry` derive from
    this class, allowing callers to catch all plugin errors at a single point.

    Attributes:
        message:     Human-readable description of the error.
        plugin_name: The name of the plugin that caused the error.
    """

    def __init__(self, message: str, plugin_name: str) -> None:
        """
        Initialise the plugin error.

        Args:
            message:     Human-readable description of the failure.
            plugin_name: Name of the plugin involved.
        """
        super().__init__(message)
        self.message = message
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


class PluginNotFoundError(PluginError):
    """
    Raised when a plugin is not found in the registry.

    Distinct from ``KeyError`` — carries ``plugin_name`` context.
    """


class DuplicatePluginError(PluginError):
    """
    Raised when a plugin with the same name is registered twice.

    The registry requires each plugin name to be unique within a single
    registry instance. Use distinct names or distinct registry instances
    for multiple plugins of the same type.
    """
