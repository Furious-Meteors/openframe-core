"""
openframe/core/testing/fakes/vector_store.py
===============================================
InMemoryVectorStore — a reusable test double for BaseVectorStore.

Extends :class:`~openframe.core.testing.fakes.repository.InMemoryRepository`
(inherits its id-addressable CRUD behaviour exactly as-is) and adds a
brute-force :meth:`search` — linear scan over every stored entity's
vector, ranked by Euclidean distance to the query vector. Fine for tests
and local development; not a stand-in for a real vector index's
performance characteristics.

Satisfies :class:`~openframe.core.ports.BaseVectorStore` structurally (no
inheritance) — including everything ``InMemoryRepository`` already
satisfies for ``BaseRepository``/``BasePort``.

.. stability: experimental
   New alongside :class:`~openframe.core.ports.BaseVectorStore` itself.

Dependency order:
    testing/fakes/vector_store → testing/fakes/repository + ports
"""
from __future__ import annotations

import math
from typing import Any, TypeVar

from openframe.core.ports import Capability
from openframe.core.testing.fakes.repository import InMemoryRepository

__all__ = ["InMemoryVectorStore"]

__stability__ = "experimental"

T = TypeVar("T")


def _get_entity_vector(entity: Any) -> list[float]:
    """Extract the entity's ``vector`` from either an attribute or a dict key."""
    val = getattr(entity, "vector", None)
    if val is None and hasattr(entity, "get"):
        val = entity.get("vector")
    if val is None:
        raise ValueError(
            f"Entity {entity!r} has no 'vector' attribute or 'vector' key. "
            "InMemoryVectorStore requires entities to expose their embedding "
            "as entity.vector (attribute) or entity['vector'] (dict key)."
        )
    return list(val)


def _euclidean_distance(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


class InMemoryVectorStore(InMemoryRepository[T]):
    """
    In-memory vector store for use in tests and local development.

    Inherits :class:`~openframe.core.testing.fakes.repository.InMemoryRepository`'s
    id-addressable CRUD behaviour unchanged, and adds:

    - ``search()`` — brute-force linear scan, ranked by Euclidean distance
      to the query vector, ascending (nearest first). An exact-match query
      vector always ranks first, matching every real metric's behaviour
      at distance/similarity extremes — this is what
      :class:`~openframe.core.testing.contracts.vector_store.VectorStoreContractTests`
      actually relies on, rather than any specific metric's tie-breaking.

    Satisfies :class:`~openframe.core.ports.BaseVectorStore` (which
    extends ``BaseRepository``/``BasePort``) via structural subtyping —
    ``isinstance(store, BaseVectorStore)`` returns ``True``.

    .. stability: experimental

    Usage::

        store = InMemoryVectorStore[Artifact]()
        await store.create(Artifact(id="1", vector=[1.0, 0.0, 0.0]))
        results = await store.search(query_vector=[1.0, 0.0, 0.0], k=1)
        assert results[0].id == "1"
    """

    def __init__(
        self,
        *,
        name: str = "in-memory-vector-store",
        version: str = "1.0.0",
        capability: Capability = Capability.SEARCH,
        healthy: bool = True,
    ) -> None:
        """
        Initialise an empty vector store.

        Args:
            name:       Identity name.
            version:    Identity version string.
            capability: Identity capability. Defaults to ``Capability.SEARCH``
                        (not ``PERSISTENCE`` — see ``InMemoryRepository``'s
                        own default — since vector stores are the ``SEARCH``
                        capability's reference adapters).
            healthy:    When ``False``, ``health()`` reports
                        ``PluginStatus.FAILED`` instead of ``READY``.
        """
        super().__init__(name=name, version=version, capability=capability, healthy=healthy)

    async def search(self, query_vector: list[float], k: int) -> list[T]:
        """
        Return the ``k`` entities whose vectors are nearest to
        ``query_vector`` by Euclidean distance.

        Brute-force linear scan over every stored entity — fine for small
        test stores, not representative of a real index's performance.

        Args:
            query_vector: The embedding to search against.
            k: Maximum number of results to return.

        Returns:
            Up to ``k`` entities, nearest first. Empty list if the store
            is empty — never raises, never returns ``None``.
        """
        scored = [
            (_euclidean_distance(query_vector, _get_entity_vector(entity)), entity)
            for entity in self._store.values()
        ]
        scored.sort(key=lambda pair: pair[0])
        return [entity for _, entity in scored[:k]]
