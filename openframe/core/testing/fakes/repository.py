"""
openframe/core/testing/fakes/repository.py
============================================
InMemoryRepository — a reusable test double.

Satisfies :class:`~openframe.core.ports.BaseRepository` and
:class:`~openframe.core.health.HealthCheck` structurally (no inheritance).
Thread-safe for asyncio single-threaded use.  Zero external dependencies.

.. stability: beta
   Beta — API may change in minor versions with a deprecation notice.

Dependency order:
    testing/fakes/repository → ports + health + exceptions
"""
from __future__ import annotations

from typing import Any, Generic, TypeVar

__all__ = ["InMemoryRepository"]

__stability__ = "beta"

T = TypeVar("T")


def _get_entity_id(entity: Any) -> str:
    """Extract the entity's ``id`` from either an attribute or a dict key."""
    val = getattr(entity, "id", None)
    if val is None and hasattr(entity, "get"):
        val = entity.get("id")
    if val is None:
        raise ValueError(
            f"Entity {entity!r} has no 'id' attribute or 'id' key.  "
            "InMemoryRepository requires entities to expose their identifier "
            "as entity.id (attribute) or entity['id'] (dict key)."
        )
    return str(val)


class InMemoryRepository(Generic[T]):
    """
    In-memory repository for use in tests and local development.

    Stores entities in a ``dict`` keyed by ``entity_id``.

    Behaviour contract:

    - ``get()``    — returns ``None`` for missing entities (never raises
                     ``AdapterNotFoundError``).
    - ``list()``   — returns entities in insertion order; respects ``limit``
                     and ``offset``; total count is always the full store size.
    - ``create()`` — stores the entity exactly as passed (no ID generation).
    - ``update()`` — returns ``None`` for missing entities.
    - ``delete()`` — returns ``False`` for missing entities.
    - ``ping()``   — always returns ``True`` (configurable for failure
                     testing via ``ping_healthy=False``).
    - ``is_ready()`` — always returns ``True`` (configurable via
                       ``ready_healthy=False``).

    Satisfies both :class:`~openframe.core.ports.BaseRepository` and
    :class:`~openframe.core.health.HealthCheck` via structural subtyping —
    ``isinstance(repo, BaseRepository)`` and
    ``isinstance(repo, HealthCheck)`` both return ``True``.

    .. stability: beta

    Usage::

        repo = InMemoryRepository[Item]()
        item = await repo.create(Item(id="1", name="test"))
        assert await repo.get("1") == item

        # Failure simulation
        repo = InMemoryRepository(ping_healthy=False)
        assert await repo.ping() is False

        # Direct store access (test assertions only)
        assert "1" in repo.store
    """

    def __init__(
        self,
        *,
        ping_healthy: bool = True,
        ready_healthy: bool = True,
    ) -> None:
        """
        Initialise an empty repository.

        Args:
            ping_healthy:  When ``False``, :meth:`ping` returns ``False``.
            ready_healthy: When ``False``, :meth:`is_ready` returns ``False``.
        """
        self._store: dict[str, T] = {}
        self._ping_healthy = ping_healthy
        self._ready_healthy = ready_healthy

    # ------------------------------------------------------------------
    # BaseRepository[T] interface
    # ------------------------------------------------------------------

    async def get(self, entity_id: str) -> T | None:
        """
        Retrieve a single entity by its identifier.

        Returns ``None`` if the entity does not exist (never raises
        ``AdapterNotFoundError``).

        Args:
            entity_id: The unique identifier of the entity.

        Returns:
            The entity if found, ``None`` otherwise.
        """
        return self._store.get(entity_id)

    async def list(self, limit: int, offset: int) -> tuple[list[T], int]:
        """
        Return a paginated slice of all entities plus the total count.

        Entities are returned in insertion order.  ``total`` is always the
        full store size regardless of ``limit`` / ``offset``.

        Args:
            limit:  Maximum number of entities to return.
            offset: Number of entities to skip from the beginning.

        Returns:
            ``(entities, total_count)`` tuple.
        """
        all_entities = list(self._store.values())
        total = len(all_entities)
        sliced = all_entities[offset : offset + limit]
        return sliced, total

    async def create(self, entity: T) -> T:
        """
        Persist a new entity and return it.

        Stores the entity exactly as passed — no ID generation.  The entity
        must already have a valid ``id`` attribute or ``id`` key.

        Args:
            entity: The entity to store.

        Returns:
            The entity as stored.
        """
        entity_id = _get_entity_id(entity)
        self._store[entity_id] = entity
        return entity

    async def update(self, entity: T) -> T | None:
        """
        Update an existing entity in the store.

        Returns ``None`` if the entity does not exist.

        Args:
            entity: The entity with updated fields.

        Returns:
            The updated entity, or ``None`` if not found.
        """
        entity_id = _get_entity_id(entity)
        if entity_id not in self._store:
            return None
        self._store[entity_id] = entity
        return entity

    async def delete(self, entity_id: str) -> bool:
        """
        Remove an entity by its identifier.

        Args:
            entity_id: The unique identifier of the entity.

        Returns:
            ``True`` if the entity was deleted, ``False`` if it did not exist.
        """
        if entity_id not in self._store:
            return False
        del self._store[entity_id]
        return True

    # ------------------------------------------------------------------
    # HealthCheck interface
    # ------------------------------------------------------------------

    async def ping(self) -> bool:
        """
        Low-cost liveness check.

        Returns the value of ``ping_healthy`` passed at construction.
        Always returns without raising.
        """
        return self._ping_healthy

    async def is_ready(self) -> bool:
        """
        Full readiness check.

        Returns the value of ``ready_healthy`` passed at construction.
        Always returns without raising.
        """
        return self._ready_healthy

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """
        Clear all stored entities.

        Intended for test setup/teardown — clears the underlying store
        without resetting health configuration.
        """
        self._store.clear()

    @property
    def store(self) -> dict[str, T]:
        """
        Direct read-only view of the underlying store.

        For test assertions only — do not mutate this dict in production code.

        Returns:
            The internal ``{entity_id: entity}`` mapping.
        """
        return self._store
