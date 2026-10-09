"""
openframe/core/testing/fakes/graph_store.py
==============================================
InMemoryGraphStore — a reusable test double for BaseGraphStore.

Extends :class:`~openframe.core.testing.fakes.repository.InMemoryRepository`
(inherits its id-addressable node CRUD behaviour exactly as-is) and adds a
toy :meth:`traverse` — not a real query-language interpreter. It
recognises exactly one convention: a ``params["id"]`` key, which it uses
to look up a single node by id, mirroring the one thing every real
backend's ``traverse()`` is actually exercised for in these contract
tests. The ``query`` string itself is accepted but ignored — a real
adapter's ``query`` argument matters (it's Cypher/Gremlin/...), but this
fake has no query engine to interpret it with. Fine for tests and local
development; not a stand-in for a real graph engine's pattern-matching.

Satisfies :class:`~openframe.core.ports.BaseGraphStore` structurally (no
inheritance) — including everything ``InMemoryRepository`` already
satisfies for ``BaseRepository``/``BasePort``.

.. stability: experimental
   New alongside :class:`~openframe.core.ports.BaseGraphStore` itself.

Dependency order:
    testing/fakes/graph_store → testing/fakes/repository + ports
"""
from __future__ import annotations

from typing import TypeVar

from openframe.core.ports import Capability
from openframe.core.testing.fakes.repository import InMemoryRepository

__all__ = ["InMemoryGraphStore"]

__stability__ = "experimental"

T = TypeVar("T")


class InMemoryGraphStore(InMemoryRepository[T]):
    """
    In-memory graph store for use in tests and local development.

    Inherits :class:`~openframe.core.testing.fakes.repository.InMemoryRepository`'s
    id-addressable node CRUD behaviour unchanged, and adds:

    - ``traverse()`` — a toy lookup, not a query-language interpreter. If
      ``params`` contains an ``"id"`` key, returns the single matching
      node (or an empty list if none exists); otherwise returns every
      stored node. The ``query`` string is accepted but not interpreted
      — this fake has no Cypher/Gremlin engine. Real adapters' own
      ``traverse()`` genuinely executes ``query`` against their backend;
      this fake exists to prove the contract's *shape* (always a list,
      never ``None``, empty when nothing matches), not to simulate
      pattern-matching.

    Satisfies :class:`~openframe.core.ports.BaseGraphStore` (which
    extends ``BaseRepository``/``BasePort``) via structural subtyping —
    ``isinstance(store, BaseGraphStore)`` returns ``True``.

    .. stability: experimental

    Usage::

        store = InMemoryGraphStore[Node]()
        await store.create(Node(id="1", name="alice"))
        results = await store.traverse("MATCH (n) WHERE n.id = $id RETURN n", {"id": "1"})
        assert results[0].id == "1"
    """

    def __init__(
        self,
        *,
        name: str = "in-memory-graph-store",
        version: str = "1.0.0",
        capability: Capability = Capability.SEARCH,
        healthy: bool = True,
    ) -> None:
        """
        Initialise an empty graph store.

        Args:
            name:       Identity name.
            version:    Identity version string.
            capability: Identity capability. Defaults to ``Capability.SEARCH``
                        (not ``PERSISTENCE`` — see ``InMemoryRepository``'s
                        own default — since graph stores are, like vector
                        stores, reference adapters for the ``SEARCH``
                        capability).
            healthy:    When ``False``, ``health()`` reports
                        ``PluginStatus.FAILED`` instead of ``READY``.
        """
        super().__init__(name=name, version=version, capability=capability, healthy=healthy)

    async def traverse(
        self, query: str, params: dict[str, object] | None = None
    ) -> list[T]:
        """
        Toy lookup standing in for a real pattern-matching query.

        Recognises one convention: ``params["id"]`` looks up a single
        node by id. Any other ``params`` shape (including ``None``)
        returns every stored node. ``query`` is accepted but ignored —
        this fake has no query engine.

        Args:
            query:  Accepted but not interpreted.
            params: If it contains an ``"id"`` key, filters to that one
                    node. ``None`` or missing ``"id"`` returns everything.

        Returns:
            A list — empty if ``params["id"]`` names a node that doesn't
            exist. Never raises, never returns ``None``.
        """
        params = params or {}
        if "id" in params:
            entity = self._store.get(str(params["id"]))
            return [entity] if entity is not None else []
        return list(self._store.values())
