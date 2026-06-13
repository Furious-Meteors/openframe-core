"""
tests/test_middleware_types.py
================================
Tests for openframe.core.middleware ASGI type aliases.

Covers:
- All 5 aliases importable from openframe.core.middleware
- All 5 aliases importable from openframe.core.middleware.types
- ASGIScope and ASGIMessage have MutableMapping as their origin type
- MutableMapping (origin) supports isinstance checks at runtime
- All aliases present in middleware.__all__

Note on isinstance with subscripted generics:
    ``isinstance({}, ASGIScope)`` raises ``TypeError`` because
    ``MutableMapping[str, Any]`` is a subscripted generic alias and
    does not support runtime isinstance. Tests use ``get_origin()``
    instead, which is the correct way to inspect type aliases.
"""
from __future__ import annotations

from collections.abc import MutableMapping
from typing import get_origin

import pytest

import openframe.core.middleware as middleware_module
import openframe.core.middleware.types as types_module
from openframe.core.middleware import (
    ASGIApp,
    ASGIMessage,
    ASGIScope,
    Receive,
    Send,
)


# ---------------------------------------------------------------------------
# Import checks — middleware package
# ---------------------------------------------------------------------------


def test_asgi_scope_importable_from_middleware() -> None:
    assert ASGIScope is not None


def test_asgi_message_importable_from_middleware() -> None:
    assert ASGIMessage is not None


def test_receive_importable_from_middleware() -> None:
    assert Receive is not None


def test_send_importable_from_middleware() -> None:
    assert Send is not None


def test_asgi_app_importable_from_middleware() -> None:
    assert ASGIApp is not None


# ---------------------------------------------------------------------------
# Import checks — types submodule
# ---------------------------------------------------------------------------


def test_asgi_scope_importable_from_types_module() -> None:
    assert types_module.ASGIScope is not None


def test_asgi_message_importable_from_types_module() -> None:
    assert types_module.ASGIMessage is not None


def test_receive_importable_from_types_module() -> None:
    assert types_module.Receive is not None


def test_send_importable_from_types_module() -> None:
    assert types_module.Send is not None


def test_asgi_app_importable_from_types_module() -> None:
    assert types_module.ASGIApp is not None


def test_middleware_and_types_module_share_same_aliases() -> None:
    """Both import paths must resolve to the same objects."""
    assert ASGIScope is types_module.ASGIScope
    assert ASGIMessage is types_module.ASGIMessage
    assert Receive is types_module.Receive
    assert Send is types_module.Send
    assert ASGIApp is types_module.ASGIApp


# ---------------------------------------------------------------------------
# Type alias origin checks (correct way to inspect subscripted aliases)
# ---------------------------------------------------------------------------


def test_asgi_scope_origin_is_mutable_mapping() -> None:
    """ASGIScope = MutableMapping[str, Any] — origin must be MutableMapping."""
    assert get_origin(ASGIScope) is MutableMapping


def test_asgi_message_origin_is_mutable_mapping() -> None:
    """ASGIMessage = MutableMapping[str, Any] — origin must be MutableMapping."""
    assert get_origin(ASGIMessage) is MutableMapping


def test_mutable_mapping_origin_supports_isinstance() -> None:
    """The unsubscripted MutableMapping is runtime-checkable."""
    assert isinstance({}, MutableMapping)


def test_isinstance_with_subscripted_asgi_scope_raises_type_error() -> None:
    """
    isinstance({}, ASGIScope) raises TypeError.

    Subscripted generics from collections.abc do not support isinstance.
    Use get_origin(ASGIScope) is MutableMapping instead.
    """
    with pytest.raises(TypeError):
        isinstance({}, ASGIScope)  # type: ignore[misc]


# ---------------------------------------------------------------------------
# __all__ completeness
# ---------------------------------------------------------------------------


def test_all_asgi_types_in_middleware_all() -> None:
    for name in ("ASGIScope", "ASGIMessage", "Receive", "Send", "ASGIApp"):
        assert name in middleware_module.__all__, (
            f"{name!r} missing from openframe.core.middleware.__all__"
        )


def test_telemetry_middleware_in_middleware_all() -> None:
    assert "TelemetryMiddleware" in middleware_module.__all__


def test_types_module_all_complete() -> None:
    for name in ("ASGIScope", "ASGIMessage", "Receive", "Send", "ASGIApp"):
        assert name in types_module.__all__, (
            f"{name!r} missing from openframe.core.middleware.types.__all__"
        )
