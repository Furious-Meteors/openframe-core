"""
openframe/core/ports/outbound/repository.py
==============================================
Generic persistence port for the OpenFrame ecosystem (ADR-006).

``BaseRepository[T]`` extends
:class:`~openframe.core.ports.port.BasePort` directly — it is
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

This module also defines :class:`BaseVectorStore`, which extends
``BaseRepository`` directly rather than sitting in its own file or as a
disjoint sibling port (the way ``BaseProducer``/``BaseConsumer`` are
siblings of ``BaseRepository``, not subtypes). Most vector databases ARE
genuinely id-addressable — insert/upsert-with-id, fetch-by-id,
delete-by-id, list/scroll — so the five CRUD methods below are real
operations for them too, not fakes forced to satisfy an interface. The
only operation with no equivalent here is similarity search, so
``BaseVectorStore`` adds exactly one new method, :meth:`BaseVectorStore.search`,
on top of everything below. A vector store that satisfies
``BaseVectorStore`` also satisfies ``BaseRepository`` for free — existing
code written against ``BaseRepository`` keeps working unmodified against
a vector-backed implementation.

``BaseVectorStore`` is deliberately not a universal fit for every
vector backend. FAISS (a bare in-process index with no native
id→metadata store, and some index types that don't support deletion
without a full rebuild) was evaluated and explicitly excluded from this
port's intended adopters.

This module also defines :class:`BaseGraphStore`, which — like
``BaseVectorStore`` — extends ``BaseRepository`` directly. A graph
database's nodes ARE genuinely id-addressable: create/get/update/delete
map onto real `CREATE`/`MATCH ... WHERE n.<key> = $id`/`SET`/`DETACH
DELETE` operations, provided the adapter addresses nodes by an
application-level unique property (with a backing index/constraint the
adapter is responsible for creating), not a backend-internal node
identity. FalkorDB's own ``id()`` function is explicitly documented as
unstable — deleted nodes' higher internal ids can be migrated down to
fill vacated lower ones — so it is unsuitable as this port's addressing
key; this is exactly why adapters must key off their own property, not
why graph databases don't fit this port at all. The one operation with
no CRUD equivalent is traversal/pattern-matching, so ``BaseGraphStore``
adds exactly one new method, :meth:`BaseGraphStore.traverse`, which also
serves as the escape hatch for relationship/edge creation and querying
(Cypher's ``CREATE``/``MATCH`` handle nodes and edges in the same
statement) — this port does not model edges as their own first-class
method, the same way it does not invent a bespoke query language.

Dependency order:
    ports/port                → ports/identity + ports/lifecycle
    ports/outbound/repository → ports/port
"""
from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

from openframe.core.ports.port import BasePort

__all__ = ["BaseRepository", "BaseVectorStore", "BaseGraphStore"]

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


@runtime_checkable
class BaseVectorStore(BaseRepository[T], Protocol[T]):
    """
    Generic vector store port. ``BaseRepository[T]`` (id-addressable CRUD)
    plus one additional domain method, :meth:`search`.

    See this module's own docstring for why this extends ``BaseRepository``
    directly rather than being a disjoint sibling port, and why FAISS/
    FalkorDB are explicitly excluded from this port's intended adopters.

    Adapters implement this protocol structurally — no inheritance needed.
    Any class with matching async method signatures, plus everything
    ``BaseRepository``/``BasePort`` require, satisfies ``BaseVectorStore``.

    Type parameter ``T`` is the domain entity the vector store manages —
    typically a dataclass or Pydantic model carrying an id, an embedding
    vector, and whatever metadata fields the caller's domain needs.

    .. stability: experimental
       New port, added alongside the first vector-store adapter packages.
       API may change based on real usage. ``BaseRepository`` above is
       unaffected by this — it remains stable; only ``BaseVectorStore``
       itself is experimental.

    Runtime check::

        isinstance(store, BaseVectorStore)   # ✓ works
        isinstance(store, BaseRepository)    # ✓ also true

    Inherited from ``BaseRepository[T]`` — id-addressable CRUD:
        get:    Fetch a single entity by id.
        list:   Return a paginated slice plus total count.
        create: Upsert a new entity (most vector DBs treat insert as
                upsert-by-id natively; adapters document their own
                create-vs-upsert semantics if they diverge).
        update: Upsert an existing entity's vector/metadata.
        delete: Remove an entity by id.

    New in this port:
        search: Similarity search — the operation ``BaseRepository`` has
                no equivalent for.

    Plus, inherited from ``BasePort`` (via ``BaseRepository``): ``name``,
    ``version``, ``capability``, ``initialize``, ``shutdown``, ``health``.
    """

    async def search(self, query_vector: list[float], k: int) -> list[T]:
        """
        Return the ``k`` entities whose vectors are most similar to
        ``query_vector``.

        The distance/similarity metric (cosine, L2, dot product, ...) is
        an adapter/backend-level configuration concern, not part of this
        port's signature — different backends default to different
        metrics, and some let it be configured per-collection at index
        creation time. Document the active metric in the adapter's own
        docstring.

        Args:
            query_vector: The embedding to search against. Must match the
                          dimensionality the backend collection/index was
                          created with — a mismatch is a configuration
                          error, not a query error, but adapters may
                          surface it as either depending on when the
                          backend itself detects it.
            k: Maximum number of results to return, ordered from most to
               least similar. Returning fewer than ``k`` results (if the
               collection has fewer than ``k`` entities, or the backend
               applies its own relevance cutoff) is not an error.

        Returns:
            Up to ``k`` entities, ordered from most to least similar.
            Empty list if nothing matches (never ``None`` — unlike
            ``get()``, "no results" is a normal outcome of a search, not
            a not-found case).

        Raises:
            AdapterConnectionError:    If the backend is unreachable.
            AdapterQueryError:         If the query fails (e.g.
                                       ``query_vector``'s dimensionality
                                       doesn't match the collection).
            AdapterTimeoutError:       If the operation exceeds
                                       ``operation_timeout``.
        """
        ...


@runtime_checkable
class BaseGraphStore(BaseRepository[T], Protocol[T]):
    """
    Generic graph store port. ``BaseRepository[T]`` (id-addressable node
    CRUD) plus one additional domain method, :meth:`traverse`.

    See this module's own docstring for why this extends ``BaseRepository``
    directly rather than being a disjoint sibling port, why FalkorDB's
    internal ``id()`` is not a suitable addressing key, and why
    relationships/edges are not given their own port method.

    Adapters implement this protocol structurally — no inheritance needed.
    Any class with matching async method signatures, plus everything
    ``BaseRepository``/``BasePort`` require, satisfies ``BaseGraphStore``.

    Type parameter ``T`` is the domain entity representing a **node** —
    typically a dataclass or Pydantic model carrying an application-level
    unique id, labels, and whatever properties the caller's domain needs.
    Edges are not modeled by ``T`` or by any method on this port; they are
    created and queried exclusively through :meth:`traverse`.

    .. stability: experimental
       New port, added alongside the first graph-store adapter packages.
       API may change based on real usage. ``BaseRepository`` above is
       unaffected by this — it remains stable; only ``BaseGraphStore``
       itself is experimental.

    Runtime check::

        isinstance(store, BaseGraphStore)    # ✓ works
        isinstance(store, BaseRepository)    # ✓ also true

    Inherited from ``BaseRepository[T]`` — id-addressable node CRUD:
        get:    Fetch a single node by its application-level id.
        list:   Return a paginated slice of nodes plus total count.
        create: Create a new node. Adapters are responsible for ensuring
                a unique constraint/index exists on the id property they
                address nodes by — without one, every get/update/delete
                degrades to an unindexed label scan.
        update: Update an existing node's properties.
        delete: Remove a node by id. Adapters should detach (remove
                incident edges) before deleting, since most graph backends
                reject deleting a node that still has relationships.

    New in this port:
        traverse: Arbitrary pattern-matching/traversal query — the
                  operation ``BaseRepository`` has no equivalent for, and
                  also the only way to create, update, or query edges.

    Plus, inherited from ``BasePort`` (via ``BaseRepository``): ``name``,
    ``version``, ``capability``, ``initialize``, ``shutdown``, ``health``.
    """

    async def traverse(
        self, query: str, params: dict[str, object] | None = None
    ) -> list[T]:
        """
        Execute an arbitrary pattern-matching/traversal query against the
        graph and return the matching entities.

        This is the escape hatch for everything ``BaseRepository``'s CRUD
        methods cannot express: multi-hop traversals, relationship/edge
        creation and querying, variable-length paths, aggregations. The
        query language itself (Cypher, Gremlin, ...) is an adapter/backend
        concern, not part of this port's signature — adapters document
        which language their ``query`` argument expects.

        Args:
            query:  A query string in the backend's native query language.
            params: Named parameters substituted into the query, keyed by
                    name as the backend's driver expects. None if the
                    query has no parameters.

        Returns:
            The entities the query's `RETURN`-equivalent clause produces.
            Empty list if the query matches nothing (not an error).

        Raises:
            AdapterConnectionError: If the backend is unreachable.
            AdapterQueryError:      If the query is malformed or fails
                                     (e.g. a syntax error, or a
                                     constraint violation on a write).
            AdapterTimeoutError:    If the operation exceeds
                                     ``operation_timeout``.
        """
        ...
