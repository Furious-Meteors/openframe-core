"""
tests/test_ports_primitives.py
================================
Tests for the port/lifecycle primitives in openframe.core.ports
(ADR-006) — previously openframe.core.contracts, merged into
openframe.core.ports in v3.1.0: Identity, Lifecycle, BasePort,
Capability, PluginStatus/PluginHealth/PluginContext, PrincipalContext,
TenantContext.
"""
from __future__ import annotations

import dataclasses

import pytest

from openframe.core.ports import (
    BasePort,
    Capability,
    Identity,
    Lifecycle,
    PluginContext,
    PluginHealth,
    PluginStatus,
    PrincipalContext,
    TenantContext,
)


# ---------------------------------------------------------------------------
# Helper concrete implementations
# ---------------------------------------------------------------------------


class FullPort:
    """Implements Identity + Lifecycle — satisfies BasePort."""

    def __init__(self) -> None:
        self.name = "full-port"
        self.version = "1.0.0"
        self.capability = Capability.PERSISTENCE

    async def initialize(self, context: PluginContext) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    async def health(self) -> PluginHealth:
        return PluginHealth(status=PluginStatus.READY)


class MissingLifecycle:
    """Has Identity attributes but no Lifecycle methods."""

    name = "missing-lifecycle"
    version = "1.0.0"
    capability = Capability.CACHE


class MissingIdentity:
    """Has Lifecycle methods but no Identity attributes."""

    async def initialize(self, context: PluginContext) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    async def health(self) -> PluginHealth:
        return PluginHealth(status=PluginStatus.READY)


# ---------------------------------------------------------------------------
# Capability
# ---------------------------------------------------------------------------


def test_capability_is_str_enum() -> None:
    assert Capability.PERSISTENCE == "persistence"
    assert isinstance(Capability.PERSISTENCE, str)


def test_capability_has_expected_members() -> None:
    expected = {
        "PERSISTENCE",
        "CACHE",
        "QUEUE",
        "SECRETS",
        "FLAGS",
        "STORAGE",
        "TRANSPORT",
        "INFERENCE",
        "EMBEDDING",
        "SCHEDULE",
        "SEARCH",
    }
    assert {m.name for m in Capability} == expected


def test_capability_str_returns_value() -> None:
    assert str(Capability.QUEUE) == "queue"


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------


def test_identity_is_runtime_checkable() -> None:
    assert (
        getattr(Identity, "_is_runtime_protocol", False)
        or hasattr(Identity, "__protocol_attrs__")
    )


def test_full_port_satisfies_identity() -> None:
    assert isinstance(FullPort(), Identity)


def test_missing_identity_fails_identity_protocol() -> None:
    assert not isinstance(MissingIdentity(), Identity)


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


def test_lifecycle_is_runtime_checkable() -> None:
    assert (
        getattr(Lifecycle, "_is_runtime_protocol", False)
        or hasattr(Lifecycle, "__protocol_attrs__")
    )


def test_full_port_satisfies_lifecycle() -> None:
    assert isinstance(FullPort(), Lifecycle)


def test_missing_lifecycle_fails_lifecycle_protocol() -> None:
    assert not isinstance(MissingLifecycle(), Lifecycle)


# ---------------------------------------------------------------------------
# BasePort
# ---------------------------------------------------------------------------


def test_base_port_is_runtime_checkable() -> None:
    assert (
        getattr(BasePort, "_is_runtime_protocol", False)
        or hasattr(BasePort, "__protocol_attrs__")
    )


def test_full_port_satisfies_base_port() -> None:
    assert isinstance(FullPort(), BasePort)


def test_missing_lifecycle_fails_base_port() -> None:
    assert not isinstance(MissingLifecycle(), BasePort)


def test_missing_identity_fails_base_port() -> None:
    assert not isinstance(MissingIdentity(), BasePort)


def test_plain_object_does_not_satisfy_base_port() -> None:
    assert not isinstance(object(), BasePort)


async def test_full_port_health_returns_plugin_health() -> None:
    port = FullPort()
    result = await port.health()
    assert isinstance(result, PluginHealth)
    assert result.status is PluginStatus.READY


# ---------------------------------------------------------------------------
# PluginHealth / PluginStatus / PluginContext
# ---------------------------------------------------------------------------


def test_plugin_health_is_frozen_dataclass() -> None:
    health = PluginHealth(status=PluginStatus.READY, message="ok")
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        health.status = PluginStatus.FAILED  # type: ignore[misc]


def test_plugin_health_defaults() -> None:
    health = PluginHealth(status=PluginStatus.REGISTERED)
    assert health.message == ""
    assert health.details == {}


def test_plugin_context_is_frozen_dataclass() -> None:
    ctx = PluginContext(config={}, plugin_name="test-ctx")
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        ctx.plugin_name = "mutated"  # type: ignore[misc]


def test_plugin_context_defaults_principal_and_tenant_to_none() -> None:
    ctx = PluginContext(config={}, plugin_name="test-ctx")
    assert ctx.principal is None
    assert ctx.tenant is None


def test_plugin_context_threads_principal_and_tenant() -> None:
    principal = PrincipalContext(principal_id="user-1")
    tenant = TenantContext(tenant_id="tenant-1")
    ctx = PluginContext(
        config={"key": "value"},
        plugin_name="test-ctx",
        principal=principal,
        tenant=tenant,
    )
    assert ctx.principal is principal
    assert ctx.tenant is tenant
    assert ctx.config == {"key": "value"}


# ---------------------------------------------------------------------------
# PrincipalContext / TenantContext
# ---------------------------------------------------------------------------


def test_principal_context_is_frozen_dataclass() -> None:
    principal = PrincipalContext(principal_id="user-1", roles=("admin",))
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        principal.principal_id = "mutated"  # type: ignore[misc]


def test_principal_context_defaults() -> None:
    principal = PrincipalContext(principal_id="user-1")
    assert principal.roles == ()
    assert principal.claims == {}


def test_tenant_context_is_frozen_dataclass() -> None:
    tenant = TenantContext(tenant_id="tenant-1", name="Acme")
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        tenant.tenant_id = "mutated"  # type: ignore[misc]


def test_tenant_context_defaults() -> None:
    tenant = TenantContext(tenant_id="tenant-1")
    assert tenant.name == ""
