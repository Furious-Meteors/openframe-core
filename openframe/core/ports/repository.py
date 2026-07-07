"""
openframe/core/ports/repository.py
=====================================
Generic persistence port for the OpenFrame ecosystem (ADR-006).

``BaseRepository[T]`` extends
:class:`~openframe.core.contracts.port.BasePort` directly — it is
``Identity + Lifecycle`` plus its own domain methods. There is exactly one
lifecycle-aware definition of this port; the pre-v3 lifecycle-free version
no longer exists.

Adapters satisfy this protocol by structural subtyping — no inheritance
from ``BaseRepository`` is required or desired. Any class whose async
method signatures match, and that also satisfies ``BasePort``
(``name``/``version``/``capability``/``initialize``/``shutdown``/
``health``), is accepted.

Runtime isinstance check::

    isinstance(repo, BaseRepository)       # ✓ works — checks method names
    isinstance(repo, BaseRepository[str])  # ✗ raises TypeError — not supported

The parameterised form is a static-analysis-only annotation. At runtime,
always check against the unparameterised ``BaseRepository``.

Dependency order:
    contracts/port      → contracts/identity + contracts/lifecycle
    ports/repository    → contracts/port
"""
from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

from openframe.core.contracts.port import BasePort

__all__ = ["BaseRepository"]

T = TypeVar("T")


@runtime_checkable
class BaseRepository(BasePort, Protocol[T]):
    """
    Generic persistence port. ``BasePort`` (Identity + Lifecycle) plus
    domain-specific CRUD methods.

    Adapters implement this protocol structurally — no inheritance needed.
    Any class with matching async method signatures, plus the
    ``BasePort`` members, satisfies ``BaseRepository``.

    Type parameter ``T`` is the domain entity the repository manages.

    Runtime check::

        isinstance(repo, BaseRepository)       # ✓ works
        isinstance(repo, BaseRepository[str])  # ✗ raises TypeError

    Domain methods:
        get:    Retrieve a single entity by ID.
        list:   Return a paginated slice plus total count.
        create: Persist a new entity and return it with any backend-assigned
                fields populated (e.g. generated primary key, created_at).
        update: Persist changes to an existing entity. Returns the updated
                entity or None if the entity did not exist.
        delete: Remove an entity by ID. Returns True if deleted, False if
                the entity did not exist.

    Plus, inherited from ``BasePort``: ``name``, ``version``, ``capability``,
    ``initialize``, ``shutdown``, ``health``.
    """

    async def get(self, entity_id: str) -> T | None:
        """
        Retrieve a single entity by its identifier.

        Args:
            entity_id: The unique identifier of the entity.

        Returns:
            The entity if found, None if it does not exist.

        Raises:
            AdapterConnectionError: If the backend is unreachable.
            AdapterQueryError:      If the query fails for any other reason.
            AdapterTimeoutError:    If the operation exceeds ``operation_timeout``.
        """
        ...

    async def list(self, limit: int, offset: int) -> tuple[list[T], int]:
        """
        Return a paginated slice of all entities plus the total count.

        Args:
            limit:  Maximum number of entities to return.
            offset: Number of entities to skip from the beginning.

        Returns:
            A 2-tuple of (entities, total_count). ``total_count`` is the
            count of all matching entities, not just the returned slice.

        Raises:
            AdapterConnectionError: If the backend is unreachable.
            AdapterQueryError:      If the query fails.
            AdapterTimeoutError:    If the operation exceeds ``operation_timeout``.
        """
        ...

    async def create(self, entity: T) -> T:
        """
        Persist a new entity and return it with backend-assigned fields.

        Args:
            entity: The entity to create. Backend may assign fields like
                    primary key or timestamps.

        Returns:
            The entity as stored, including any backend-assigned fields.

        Raises:
            AdapterConnectionError: If the backend is unreachable.
            AdapterQueryError:      If the insert fails (e.g. constraint violation).
            AdapterTimeoutError:    If the operation exceeds ``operation_timeout``.
        """
        ...

    async def update(self, entity: T) -> T | None:
        """
        Persist changes to an existing entity.

        Args:
            entity: The entity with updated fields. Must have a valid identifier.

        Returns:
            The updated entity as stored, or None if the entity did not exist.

        Raises:
            AdapterConnectionError: If the backend is unreachable.
            AdapterQueryError:      If the update fails.
            AdapterTimeoutError:    If the operation exceeds ``operation_timeout``.
        """
        ...

    async def delete(self, entity_id: str) -> bool:
        """
        Remove an entity by its identifier.

        Args:
            entity_id: The unique identifier of the entity to delete.

        Returns:
            True if the entity was deleted, False if it did not exist.

        Raises:
            AdapterConnectionError: If the backend is unreachable.
            AdapterQueryError:      If the deletion fails.
            AdapterTimeoutError:    If the operation exceeds ``operation_timeout``.
        """
        ...
