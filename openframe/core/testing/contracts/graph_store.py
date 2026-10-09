"""
openframe/core/testing/contracts/graph_store.py
==================================================
GraphStoreContractTests — reusable pytest base class.

Every ``openframe-adapters-db-{falkordb,...}`` package must inherit this
class and pass every test. Builds on
:class:`~openframe.core.testing.contracts.repository.RepositoryContractTests`
for the full id-addressable node CRUD contract (which itself builds on
:class:`~openframe.core.testing.contracts.port.PortContractTests` for
``BasePort`` identity + lifecycle), adding
:meth:`~openframe.core.ports.BaseGraphStore.traverse`-specific assertions
on top.

The traverse assertions are deliberately query-language-agnostic — they
never hardcode Cypher (or any other graph query language) syntax, since
different backends use different languages. Instead, each assertion asks
a fixture, ``traverse_query_for``, to produce a ``(query, params)`` pair
in whatever language the adapter under test actually speaks, that is
guaranteed to return exactly the one entity passed to it. This mirrors
how :class:`~openframe.core.testing.contracts.vector_store.VectorStoreContractTests`
asks for an ``entity_vector`` extractor rather than assuming a specific
similarity metric.

No top-level pytest import — this module can be imported without pytest
installed, matching every other module in this package.

.. stability: experimental
   New alongside :class:`~openframe.core.ports.BaseGraphStore` itself.

Dependency order:
    testing/contracts/graph_store → testing/contracts/repository + ports

Subclass usage::

    class TestFalkorDBGraphStore(GraphStoreContractTests):
        @pytest.fixture
        async def repository(self, falkordb_settings):
            return FalkorDBNodeStore(falkordb_settings)

        @pytest.fixture
        def port(self, repository):
            return repository

        @pytest.fixture
        def make_entity(self):
            def _make(id: str, name: str = "test") -> Node:
                return Node(id=id, name=name)
            return _make

        @pytest.fixture
        def traverse_query_for(self):
            # Given an entity, return a (query, params) pair that, run
            # through traverse(), returns exactly that entity.
            def _query_for(entity):
                return "MATCH (n) WHERE n.id = $id RETURN n", {"id": entity.id}
            return _query_for
"""
from __future__ import annotations

from openframe.core.testing.contracts.repository import RepositoryContractTests

__all__ = ["GraphStoreContractTests"]

__stability__ = "experimental"


class GraphStoreContractTests(RepositoryContractTests):
    """
    Reusable pytest base class for graph store contract tests.

    Subclasses must provide everything
    :class:`~openframe.core.testing.contracts.repository.RepositoryContractTests`
    requires (``repository``, ``port``, ``make_entity``), plus:

    ``traverse_query_for``
        A callable ``(entity: T) -> tuple[str, dict[str, object]]`` that,
        given an entity, returns a ``(query, params)`` pair in the
        adapter's own query language that — once the entity has been
        created — returns exactly that one entity when passed to
        :meth:`~openframe.core.ports.BaseGraphStore.traverse`. Lets these
        contract tests exercise ``traverse()`` without hardcoding Cypher
        (or any other) syntax.

    .. stability: experimental
    """

    # ------------------------------------------------------------------
    # traverse
    # ------------------------------------------------------------------

    async def test_traverse_returns_empty_list_when_nothing_matches(
        self, repository, make_entity, traverse_query_for
    ) -> None:
        """traverse() returns an empty list, never None, when nothing matches."""
        entity = make_entity(id="traverse-absent")
        query, params = traverse_query_for(entity)

        results = await repository.traverse(query, params)

        assert results == []

    async def test_traverse_returns_created_entity(
        self, repository, make_entity, traverse_query_for
    ) -> None:
        """traverse() returns an entity once it has been created."""
        entity = make_entity(id="traverse-target")
        await repository.create(entity)
        query, params = traverse_query_for(entity)

        results = await repository.traverse(query, params)

        assert entity in results

    async def test_traverse_result_is_a_list(
        self, repository, make_entity, traverse_query_for
    ) -> None:
        """traverse() always returns a list, regardless of match count."""
        entity = make_entity(id="traverse-shape")
        query, params = traverse_query_for(entity)

        results = await repository.traverse(query, params)

        assert isinstance(results, list)

    async def test_traverse_accepts_no_params(self, repository) -> None:
        """traverse() accepts params=None for queries with no parameters."""
        results = await repository.traverse("RETURN 1", None)
        assert isinstance(results, list)

    # ------------------------------------------------------------------
    # Protocol isinstance check
    # ------------------------------------------------------------------

    async def test_satisfies_base_graph_store_protocol(self, repository) -> None:
        """Graph store satisfies BaseGraphStore via structural subtyping."""
        from openframe.core.ports import BaseGraphStore

        assert isinstance(repository, BaseGraphStore), (
            f"{type(repository).__name__} does not satisfy BaseGraphStore. "
            "Ensure it implements traverse, plus everything BaseRepository/"
            "BasePort require."
        )
