"""
openframe/core/testing/fakes/repository.py
============================================
InMemoryRepository — a reusable test double (ADR-006).

Satisfies :class:`~openframe.core.ports.BaseRepository` structurally (no
inheritance) — including the ``BasePort`` identity/lifecycle members it now
extends. Thread-safe for asyncio single-threaded use. Zero external
dependencies.

.. stability: beta
   Beta — API may change in minor versions with a deprecation notice.

Dependency order:
    testing/fakes/repository → contracts + ports + exceptions
"""
from __future__ import annotations

from typing import Any, Generic, TypeVar

from openframe.core.contracts import Capability, PluginContext, PluginHealth, PluginStatus

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
    - ``initialize()`` / ``shutdown()`` — no-ops that flip an internal
      ``_initialized`` flag; ``shutdown()`` is idempotent and safe to call
      before ``initialize()``.
    - ``health()`` — returns ``PluginHealth(status=READY)`` once initialized
                     and healthy, ``FAILED`` when constructed with
                     ``healthy=False`` (configurable for failure-path
                     testing).

    Satisfies :class:`~openframe.core.ports.BaseRepository` (which now
    extends ``BasePort``) via structural subtyping —
    ``isinstance(repo, BaseRepository)`` returns ``True``.

    .. stability: beta

    Usage::

        repo = InMemoryRepository[Item]()
        item = await repo.create(Item(id="1", name="test"))
        assert await repo.get("1") == item

        # Failure simulation
        repo = InMemoryRepository(healthy=False)
        health = await repo.health()
        assert health.status is PluginStatus.FAILED

        # Direct store access (test assertions only)
        assert "1" in repo.store
    """

    def __init__(
        self,
        *,
        name: str = "in-memory-repository",
        version: str = "1.0.0",
        capability: Capability = Capability.PERSISTENCE,
        healthy: bool = True,
    ) -> None:
        """
        Initialise an empty repository.

        Args:
            name:       Identity name — see :class:`~openframe.core.contracts.identity.Identity`.
            version:    Identity version string.
            capability: Identity capability. Defaults to ``Capability.PERSISTENCE``.
            healthy:    When ``False``, :meth:`health` reports
                        ``PluginStatus.FAILED`` instead of ``READY``.
        """
        self._store: dict[str, T] = {}
        self.name = name
        self.version = version
        self.capability = capability
        self._healthy = healthy
        self._initialized = False

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
    # BasePort (Identity + Lifecycle) interface
    # ------------------------------------------------------------------

    async def initialize(self, context: PluginContext) -> None:
        """
        Mark the repository as initialized.

        No-op beyond flipping the internal flag consulted by :meth:`health`
        — the in-memory store is already usable immediately.

        Args:
            context: Ignored beyond being a valid ``PluginContext`` — the
                     fake has no external configuration to read.
        """
        self._initialized = True

    async def shutdown(self) -> None:
        """
        Mark the repository as no longer initialized.

        Idempotent — safe to call multiple times, including before
        :meth:`initialize` has ever been called. Does not clear the store;
        use :meth:`clear` for that.
        """
        self._initialized = False

    async def health(self) -> PluginHealth:
        """
        Return the current health snapshot.

        Returns ``PluginStatus.READY`` when initialized and ``healthy=True``
        was passed at construction; ``PluginStatus.FAILED`` when
        ``healthy=False``; ``PluginStatus.REGISTERED`` when not yet
        initialized. Always returns without raising.
        """
        if not self._healthy:
            return PluginHealth(status=PluginStatus.FAILED, message="simulated failure")
        if not self._initialized:
            return PluginHealth(status=PluginStatus.REGISTERED)
        return PluginHealth(status=PluginStatus.READY)

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
