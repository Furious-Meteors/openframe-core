"""
openframe/core/exceptions/codes.py
====================================
Typed error taxonomy for the OpenFrame ecosystem.

``ErrorCode`` and ``Severity`` are ``StrEnum`` members — every value is a
plain string, so it serialises cleanly across process boundaries (gRPC /
HTTP / MCP) and can be used directly as an OTel span attribute or a
low-cardinality metric label.

Decentralised ``domain.kind`` convention
----------------------------------------
Every error code is a lowercase ``"<domain>.<kind>"`` string where
``<domain>`` is the owning package's namespace (``adapter``, ``plugin``,
and, in downstream packages, ``ai``, ``transport``, ``storage``, ...).

``ErrorCode`` enumerates only the codes owned by ``openframe-core`` itself.
Downstream packages do **not** extend this enum — they declare their own
plain ``"<domain>.<kind>"`` strings following the same convention. The
:attr:`~openframe.core.exceptions.base.OpenFrameError.code` field is typed
``str`` precisely so the taxonomy can grow per-package without a central
registry every package must edit.

Stability
---------
Error codes are a stable contract within a major version — an existing
code's string value never changes until the next major release.

Dependency order: this module has no imports from openframe.core.

.. stability: stable
"""
from __future__ import annotations

from enum import StrEnum

__all__ = ["Severity", "ErrorCode"]

__stability__ = "stable"


class Severity(StrEnum):
    """
    Severity of an :class:`~openframe.core.exceptions.base.OpenFrameError`.

    Carried as data so upper layers (middleware, gateways, alerting) can act
    on severity without importing or knowing the concrete error class.
    """

    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCode(StrEnum):
    """
    Error codes owned by ``openframe-core``.

    Values follow the ``domain.kind`` convention. Downstream packages define
    their own plain-string codes rather than extending this enum.
    """

    # Generic root
    OPENFRAME = "openframe.error"

    # adapter.* — backend/infrastructure operation failures
    ADAPTER = "adapter.error"
    ADAPTER_CONNECTION = "adapter.connection"
    ADAPTER_QUERY = "adapter.query"
    ADAPTER_NOT_FOUND = "adapter.not_found"
    ADAPTER_CONFIGURATION = "adapter.configuration"
    ADAPTER_TIMEOUT = "adapter.timeout"

    # plugin.* — registry / lifecycle orchestration failures
    PLUGIN = "plugin.error"
    PLUGIN_INITIALIZATION = "plugin.initialization"
    PLUGIN_NOT_FOUND = "plugin.not_found"
    PLUGIN_DUPLICATE = "plugin.duplicate"
    CAPABILITY_AMBIGUOUS = "plugin.capability_ambiguous"
