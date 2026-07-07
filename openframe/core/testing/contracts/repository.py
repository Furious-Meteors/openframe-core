"""
openframe/core/testing/contracts/repository.py
================================================
RepositoryContractTests — reusable pytest base class (ADR-006).

Every ``openframe-adapters-db-*`` package must inherit this class and
pass every test. Tests operate at the behavioural level — no real backend
is required for :class:`~openframe.core.testing.fakes.InMemoryRepository`;
a real backend is required for Postgres, Mongo, etc.

Builds on :class:`~openframe.core.testing.contracts.port.PortContractTests`
for the full ``BasePort`` (identity + lifecycle) contract, adding
domain-specific CRUD assertions on top.

No top-level pytest import — this module can be imported without pytest
installed. The test methods use pytest's fixture injection mechanism
through parameter names; pytest is discovered at collection time.

.. stability: beta
   Beta — API may change in minor versions with a deprecation notice.

Dependency order:
    testing/contracts/repository → testing/contracts/port + ports + testing/fakes

Subclass usage::

    class TestInMemoryRepository(RepositoryContractTests):
        @pytest.fixture
        def repository(self) -> InMemoryRepository:
            return InMemoryRepository()

        @pytest.fixture
        def port(self, repository) -> InMemoryRepository:
            return repository

        @pytest.fixture
        def make_entity(self):
            def _make(id: str, name: str = "test") -> dict:
                return {"id": id, "name": name}
            return _make

    class TestPostgresRepository(RepositoryContractTests):
        @pytest.fixture
        async def repository(self, postgres_settings):
            return ItemPostgresRepository(postgres_settings)

        @pytest.fixture
        def port(self, repository):
            return repository

        @pytest.fixture
        def make_entity(self):
            def _make(id: str, name: str = "test") -> Item:
                return Item(id=id, name=name)
            return _make
"""
from __future__ import annotations

from openframe.core.testing.contracts.port import PortContractTests

__all__ = ["RepositoryContractTests"]


class RepositoryContractTests(PortContractTests):
    """
    Reusable pytest base class for repository contract tests.

    Subclasses must provide three pytest fixtures:

    ``repository``
        A :class:`~openframe.core.ports.BaseRepository` instance to test.

    ``port``
        Typically an alias of ``repository`` (``return repository``) — lets
        the inherited :class:`~openframe.core.testing.contracts.port.PortContractTests`
        identity/lifecycle checks run against the same instance.

    ``make_entity``
        A callable ``(id: str, name: str = "test") -> T`` that creates
        test entities compatible with the repository.

    Every ``test_*`` method in this class (and its
    :class:`~openframe.core.testing.contracts.port.PortContractTests` base)
    is discovered and run by pytest on the concrete subclass.

    .. stability: beta
    """

    # ------------------------------------------------------------------
    # create
    # ------------------------------------------------------------------

    async def test_create_returns_entity(self, repository, make_entity) -> None:
        """create() returns the entity that was passed in."""
        entity = make_entity(id="create-1")
        result = await repository.create(entity)
        assert result == entity

    # ------------------------------------------------------------------
    # get
    # ------------------------------------------------------------------

    async def test_get_returns_entity_after_create(self, repository, make_entity) -> None:
        """get() retrieves an entity that was previously created."""
        entity = make_entity(id="get-1")
        await repository.create(entity)
        result = await repository.get("get-1")
        assert result == entity

    async def test_get_returns_none_for_missing_entity(self, repository, make_entity) -> None:
        """get() returns None when the entity does not exist."""
        result = await repository.get("does-not-exist")
        assert result is None

    # ------------------------------------------------------------------
    # list
    # ------------------------------------------------------------------

    async def test_list_returns_empty_on_empty_store(self, repository, make_entity) -> None:
        """list() returns an empty list and zero total on an empty store."""
        entities, total = await repository.list(limit=10, offset=0)
        assert entities == []
        assert total == 0

    async def test_list_returns_created_entities(self, repository, make_entity) -> None:
        """list() returns all created entities."""
        e1 = make_entity(id="list-1", name="alpha")
        e2 = make_entity(id="list-2", name="beta")
        await repository.create(e1)
        await repository.create(e2)
        entities, total = await repository.list(limit=10, offset=0)
        assert e1 in entities
        assert e2 in entities
        assert total == 2

    async def test_list_total_count_equals_full_count(self, repository, make_entity) -> None:
        """total_count reflects the number of all entities, not the page size."""
        for i in range(5):
            await repository.create(make_entity(id=f"total-{i}"))
        _, total = await repository.list(limit=2, offset=0)
        assert total == 5

    async def test_list_respects_limit(self, repository, make_entity) -> None:
        """list() returns at most limit entities."""
        for i in range(5):
            await repository.create(make_entity(id=f"limit-{i}"))
        entities, _ = await repository.list(limit=3, offset=0)
        assert len(entities) == 3

    async def test_list_respects_offset(self, repository, make_entity) -> None:
        """list() skips offset entities from the beginning."""
        for i in range(5):
            await repository.create(make_entity(id=f"offset-{i}"))
        entities_page1, _ = await repository.list(limit=5, offset=0)
        entities_page2, _ = await repository.list(limit=5, offset=2)
        assert len(entities_page2) == 3
        assert entities_page2 == entities_page1[2:]

    # ------------------------------------------------------------------
    # update
    # ------------------------------------------------------------------

    async def test_update_returns_updated_entity(self, repository, make_entity) -> None:
        """update() returns the updated entity after a successful update."""
        entity = make_entity(id="update-1", name="original")
        await repository.create(entity)
        updated = make_entity(id="update-1", name="modified")
        result = await repository.update(updated)
        assert result == updated

    async def test_update_returns_none_for_missing_entity(self, repository, make_entity) -> None:
        """update() returns None when the entity does not exist."""
        entity = make_entity(id="update-missing")
        result = await repository.update(entity)
        assert result is None

    # ------------------------------------------------------------------
    # delete
    # ------------------------------------------------------------------

    async def test_delete_returns_true_when_deleted(self, repository, make_entity) -> None:
        """delete() returns True when the entity existed and was removed."""
        entity = make_entity(id="delete-1")
        await repository.create(entity)
        result = await repository.delete("delete-1")
        assert result is True

    async def test_delete_returns_false_when_missing(self, repository, make_entity) -> None:
        """delete() returns False when the entity does not exist."""
        result = await repository.delete("delete-never-existed")
        assert result is False

    # ------------------------------------------------------------------
    # Protocol isinstance check
    # ------------------------------------------------------------------

    async def test_satisfies_base_repository_protocol(self, repository, make_entity) -> None:
        """Repository satisfies BaseRepository via structural subtyping."""
        from openframe.core.ports import BaseRepository

        assert isinstance(repository, BaseRepository), (
            f"{type(repository).__name__} does not satisfy BaseRepository. "
            "Ensure it implements get, list, create, update, delete, plus "
            "the BasePort identity/lifecycle members."
        )
