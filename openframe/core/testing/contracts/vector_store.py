"""
openframe/core/testing/contracts/vector_store.py
===================================================
VectorStoreContractTests — reusable pytest base class.

Every ``openframe-adapters-db-{milvus,qdrant,chromadb}`` package must
inherit this class and pass every test. Builds on
:class:`~openframe.core.testing.contracts.repository.RepositoryContractTests`
for the full id-addressable CRUD contract (which itself builds on
:class:`~openframe.core.testing.contracts.port.PortContractTests` for
``BasePort`` identity + lifecycle), adding :meth:`~openframe.core.ports.BaseVectorStore.search`-specific
assertions on top.

The search assertions are deliberately metric-agnostic — they never
assert a specific similarity score or a specific ranking among
approximately-similar vectors, since different backends default to
different metrics (cosine, L2, dot product) and would legitimately rank
near-ties differently. Instead, each assertion uses an exact-match query
vector (identical to one stored entity's vector), which must rank first
under any reasonable metric — distance 0 / similarity 1 is extremal
regardless of which metric a backend uses.

No top-level pytest import — this module can be imported without pytest
installed, matching every other module in this package.

.. stability: experimental
   New alongside :class:`~openframe.core.ports.BaseVectorStore` itself.

Dependency order:
    testing/contracts/vector_store → testing/contracts/repository + ports

Subclass usage::

    class TestQdrantVectorStore(VectorStoreContractTests):
        @pytest.fixture
        async def repository(self, qdrant_settings):
            return ArtifactQdrantStore(qdrant_settings)

        @pytest.fixture
        def port(self, repository):
            return repository

        @pytest.fixture
        def make_entity(self):
            def _make(id: str, name: str = "test", vector: list[float] | None = None) -> Artifact:
                return Artifact(id=id, name=name, vector=vector or [1.0, 0.0, 0.0])
            return _make

        @pytest.fixture
        def entity_vector(self):
            # Given an entity, return its stored vector — lets the contract
            # tests build a query vector without knowing the entity's shape.
            return lambda entity: entity.vector
"""
from __future__ import annotations

from openframe.core.testing.contracts.repository import RepositoryContractTests

__all__ = ["VectorStoreContractTests"]

__stability__ = "experimental"


class VectorStoreContractTests(RepositoryContractTests):
    """
    Reusable pytest base class for vector store contract tests.

    Subclasses must provide everything
    :class:`~openframe.core.testing.contracts.repository.RepositoryContractTests`
    requires (``repository``, ``port``, ``make_entity``), plus:

    ``make_entity``
        Extended here versus the plain repository contract: must accept
        an optional ``vector: list[float] | None`` keyword argument,
        defaulting to a fixed test vector when omitted, so the inherited
        CRUD tests (which never pass ``vector``) keep working unmodified.

    ``entity_vector``
        A callable ``(entity: T) -> list[float]`` that extracts the
        stored vector back out of an entity — lets these contract tests
        build a query vector without knowing the entity's concrete shape.

    .. stability: experimental
    """

    # ------------------------------------------------------------------
    # search
    # ------------------------------------------------------------------

    async def test_search_returns_empty_list_on_empty_store(self, repository) -> None:
        """search() returns an empty list, never None, when nothing matches."""
        results = await repository.search(query_vector=[1.0, 0.0, 0.0], k=5)
        assert results == []

    async def test_search_exact_match_ranks_first(
        self, repository, make_entity, entity_vector
    ) -> None:
        """
        An entity whose vector exactly matches the query vector must be
        the top (and, with k=1, only) result — true under any similarity
        metric, so this assertion is backend-agnostic.
        """
        target = make_entity(id="search-target", vector=[1.0, 0.0, 0.0])
        decoy_a = make_entity(id="search-decoy-a", vector=[0.0, 1.0, 0.0])
        decoy_b = make_entity(id="search-decoy-b", vector=[0.0, 0.0, 1.0])
        await repository.create(target)
        await repository.create(decoy_a)
        await repository.create(decoy_b)

        results = await repository.search(query_vector=entity_vector(target), k=1)

        assert len(results) == 1
        assert results[0] == target

    async def test_search_respects_k(self, repository, make_entity) -> None:
        """search() returns at most k entities."""
        for i in range(5):
            await repository.create(
                make_entity(id=f"search-k-{i}", vector=[float(i), 0.0, 0.0])
            )
        results = await repository.search(query_vector=[0.0, 0.0, 0.0], k=3)
        assert len(results) <= 3

    async def test_search_returns_fewer_than_k_without_error(
        self, repository, make_entity
    ) -> None:
        """
        Returning fewer than k results, because the store has fewer than
        k entities, is a normal outcome — not an error.
        """
        await repository.create(make_entity(id="search-only-one", vector=[1.0, 0.0, 0.0]))
        results = await repository.search(query_vector=[1.0, 0.0, 0.0], k=10)
        assert len(results) <= 10
        assert len(results) >= 1

    # ------------------------------------------------------------------
    # Protocol isinstance check
    # ------------------------------------------------------------------

    async def test_satisfies_base_vector_store_protocol(self, repository, make_entity) -> None:
        """Vector store satisfies BaseVectorStore via structural subtyping."""
        from openframe.core.ports import BaseVectorStore

        assert isinstance(repository, BaseVectorStore), (
            f"{type(repository).__name__} does not satisfy BaseVectorStore. "
            "Ensure it implements search, plus everything BaseRepository/"
            "BasePort require."
        )
