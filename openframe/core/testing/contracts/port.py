"""
openframe/core/testing/contracts/port.py
===========================================
PortContractTests — reusable pytest base class for
:class:`~openframe.core.ports.port.BasePort` conformance (ADR-006).

Combines identity checks (``name``/``version``/``capability`` present and
correctly typed) with the full
:class:`~openframe.core.testing.contracts.lifecycle.LifecycleContractTests`
suite. Every port-specific contract-test base
(``RepositoryContractTests``, ``ProducerContractTests``,
``ConsumerContractTests``) extends this class.

No top-level pytest import — this module can be imported without pytest
installed.

.. stability: beta
   Beta — API may change in minor versions with a deprecation notice.

Dependency order:
    testing/contracts/lifecycle → ports
    testing/contracts/port      → testing/contracts/lifecycle + ports

Subclass usage::

    class TestMyAdapterPort(PortContractTests):
        @pytest.fixture
        def port(self) -> MyAdapter:
            return MyAdapter()
"""
from __future__ import annotations

from openframe.core.testing.contracts.lifecycle import LifecycleContractTests

__all__ = ["PortContractTests"]


class PortContractTests(LifecycleContractTests):
    """
    Reusable pytest base class for full ``BasePort`` contract tests.

    Subclasses must provide one pytest fixture:

    ``port``
        A fresh instance to test. Must satisfy
        :class:`~openframe.core.ports.port.BasePort`.

    Adds identity-shape checks on top of the inherited
    :class:`~openframe.core.testing.contracts.lifecycle.LifecycleContractTests`
    lifecycle suite (initialize -> health -> idempotent shutdown ->
    shutdown-before-initialize safety).

    .. stability: beta
    """

    async def test_satisfies_base_port_protocol(self, port) -> None:
        """Port satisfies BasePort via structural subtyping."""
        from openframe.core.ports import BasePort

        assert isinstance(port, BasePort), (
            f"{type(port).__name__} does not satisfy BasePort. Ensure it "
            "has 'name'/'version'/'capability' attributes and "
            "'initialize'/'shutdown'/'health' async methods."
        )

    async def test_identity_name_is_str(self, port) -> None:
        """port.name is a non-empty str."""
        assert isinstance(port.name, str) and port.name, (
            f"{type(port).__name__}.name must be a non-empty str, got {port.name!r}."
        )

    async def test_identity_version_is_str(self, port) -> None:
        """port.version is a non-empty str."""
        assert isinstance(port.version, str) and port.version, (
            f"{type(port).__name__}.version must be a non-empty str, got {port.version!r}."
        )

    async def test_identity_capability_is_capability_enum(self, port) -> None:
        """port.capability is a member of the Capability enum."""
        from openframe.core.ports import Capability

        assert isinstance(port.capability, Capability), (
            f"{type(port).__name__}.capability must be a Capability enum "
            f"member, got {port.capability!r} ({type(port.capability).__name__})."
        )
