"""
openframe/core/testing/contracts/lifecycle.py
================================================
LifecycleContractTests — reusable pytest base class for
:class:`~openframe.core.ports.lifecycle.Lifecycle` conformance
(ADR-006).

Every port implementation exercises the same lifecycle sequence:
initialize -> health -> idempotent shutdown. This class also covers the
"rollback" half of the ADR-006 lifecycle guarantee at the single-port
level: ``shutdown()`` must be safe to call even when the port was never
initialized (or initialization failed) — this is what makes
:meth:`~openframe.core.plugins.registry.PluginRegistry.initialize_all`'s
rollback-on-failure path safe, since it calls ``shutdown()`` on every
already-initialized port without knowing whether a later port's
initialization is what triggered the rollback. The *multi-port* rollback
sequencing itself (register several ports, fail one, assert the earlier
ones were shut down in reverse order) is exercised at the registry level —
see ``tests/test_plugins.py`` — because it is a property of
``PluginRegistry.initialize_all()``, not of any single ``Lifecycle``
implementation.

No top-level pytest import — this module can be imported without pytest
installed.

.. stability: beta
   Beta — API may change in minor versions with a deprecation notice.

Dependency order:
    testing/contracts/lifecycle → ports

Subclass usage::

    class TestMyAdapterLifecycle(LifecycleContractTests):
        @pytest.fixture
        def port(self) -> MyAdapter:
            return MyAdapter()
"""
from __future__ import annotations

__all__ = ["LifecycleContractTests"]


class LifecycleContractTests:
    """
    Reusable pytest base class for
    :class:`~openframe.core.ports.lifecycle.Lifecycle` contract tests.

    Subclasses must provide one pytest fixture:

    ``port``
        A fresh, un-initialized object satisfying
        :class:`~openframe.core.ports.lifecycle.Lifecycle` (and
        typically :class:`~openframe.core.ports.port.BasePort` as a
        whole — see :class:`~openframe.core.testing.contracts.port.PortContractTests`).

    Subclasses may optionally override the ``plugin_context`` fixture to
    supply a custom :class:`~openframe.core.ports.health.PluginContext`;
    the default is an empty config keyed by the port's own name.

    .. stability: beta
    """

    def _make_context(self, port):
        """Build a default PluginContext — empty config, no principal/tenant.

        Not a pytest fixture (this module has no top-level pytest import so
        it can be imported without pytest installed) — a plain helper
        method any test method can call directly.
        """
        from openframe.core.ports import PluginContext

        return PluginContext(config={}, plugin_name=getattr(port, "name", "contract-test"))

    async def test_initialize_completes_without_raising(self, port) -> None:
        """initialize() completes for a fresh port given a valid context."""
        await port.initialize(self._make_context(port))

    async def test_health_after_initialize_returns_plugin_health(self, port) -> None:
        """health() returns a PluginHealth instance after initialize()."""
        from openframe.core.ports import PluginHealth

        await port.initialize(self._make_context(port))
        result = await port.health()
        assert isinstance(result, PluginHealth), (
            f"{type(port).__name__}.health() returned {result!r}, "
            "expected a PluginHealth instance."
        )

    async def test_health_never_raises(self, port) -> None:
        """health() must not raise, whether or not initialize() was called."""
        try:
            await port.health()
        except Exception as exc:  # noqa: BLE001
            raise AssertionError(f"health() raised {exc!r}") from exc

    async def test_shutdown_is_idempotent(self, port) -> None:
        """shutdown() can be called multiple times without raising."""
        await port.initialize(self._make_context(port))
        await port.shutdown()
        await port.shutdown()

    async def test_shutdown_without_initialize_does_not_raise(self, port) -> None:
        """
        shutdown() is safe to call on a port that was never initialized.

        This is the property PluginRegistry.initialize_all()'s rollback
        path depends on being unnecessary to check for — it only calls
        shutdown() on ports it successfully initialized — but any port
        that might be shut down via other paths (e.g. a bootstrap that
        registers but never starts) must still tolerate it.
        """
        try:
            await port.shutdown()
        except Exception as exc:  # noqa: BLE001
            raise AssertionError(
                f"shutdown() raised {exc!r} when called before initialize()"
            ) from exc
