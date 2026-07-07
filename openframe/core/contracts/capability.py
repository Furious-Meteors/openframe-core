"""
openframe/core/contracts/capability.py
========================================
Closed capability taxonomy for the OpenFrame plugin/port ecosystem.

Every :class:`~openframe.core.contracts.identity.Identity` declares a
``capability`` — its logical role in the system (persistence, cache, queue,
...). Prior to v3.0 this was a raw ``str``; ADR-006 replaces it with a typed,
closed ``Enum`` so capability lookups are checked statically and
:class:`~openframe.core.plugins.registry.PluginRegistry` has a discoverable,
finite vocabulary to key on.

See ``docs/technical/architecture/capability-taxonomy.md`` for the
human-readable reference derived from this enum.

Dependency order: this module imports only from Python stdlib.
No openframe.core imports.
"""
from __future__ import annotations

from enum import Enum

__all__ = ["Capability"]


class Capability(str, Enum):
    """
    Closed taxonomy of logical adapter roles.

    Subclasses ``str`` so members compare equal to their value
    (``Capability.PERSISTENCE == "persistence"``) and serialise cleanly to
    JSON/logs without an explicit ``.value`` access.

    Members:
        PERSISTENCE: Durable storage of domain entities (SQL, NoSQL).
        CACHE:       Ephemeral, fast key-value storage.
        QUEUE:       Asynchronous message production/consumption.
        SECRETS:     Secret material retrieval (API keys, credentials).
        FLAGS:       Feature flag / toggle evaluation.
        STORAGE:     Blob/object storage (files, images, artifacts).
        TRANSPORT:   Synchronous network transport (HTTP client, gRPC).
        INFERENCE:   Model inference (LLM completion, classification).
        EMBEDDING:   Vector embedding generation.
        SCHEDULE:    Deferred/recurring task scheduling.
        SEARCH:      Full-text or vector search/retrieval.
    """

    PERSISTENCE = "persistence"
    CACHE = "cache"
    QUEUE = "queue"
    SECRETS = "secrets"
    FLAGS = "flags"
    STORAGE = "storage"
    TRANSPORT = "transport"
    INFERENCE = "inference"
    EMBEDDING = "embedding"
    SCHEDULE = "schedule"
    SEARCH = "search"

    def __str__(self) -> str:
        return self.value
