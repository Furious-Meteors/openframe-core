"""
openframe.core.schemas
========================
Cross-service data shape governance (ADR-007).

The @contract decorator marks a Pydantic model as a published
cross-service contract — a shape that crosses a service boundary
(via REST, Kafka, gRPC, or any other transport) and must be
governed for breaking changes.

This module owns only the *marker*. The machinery that acts on
the marker — schema export, version registry, breaking-change diff,
codegen — lives in the separate openframe-schemas package, which
has its own dependencies and release cadence.

Dependency order:
    core/schemas → stdlib only (no pydantic, no openframe imports)

Usage::

    from openframe.core.schemas import contract

    @contract(name="item", version="1.0")
    class Item(BaseModel):
        id: str
        name: str
        description: str | None = None
        status: str = "active"

The @contract decorator does not change the class in any way that
affects Pydantic validation, serialization, or runtime behaviour.
It attaches __contract__ as a class attribute that openframe-schemas
reads at schema-export time.

.. stability: experimental
   Experimental — the decorator signature (name, version) is stable;
   the ContractMeta attributes may gain additional fields in future
   minor versions.
"""
from __future__ import annotations

from dataclasses import dataclass

__all__ = ["ContractMeta", "contract", "get_contract_meta"]

__stability__ = "experimental"


@dataclass
class ContractMeta:
    """
    Metadata attached to a @contract-decorated model.

    .. stability: experimental

    Attributes:
        name:    The contract's stable name (e.g. ``"item"``). Identifies
                 the contract independently of the Python class name.
        version: The contract's version string (e.g. ``"1.0"``). Governed
                 by openframe-schemas' breaking-change diff tooling.
    """

    name: str
    version: str

    __stability__ = "experimental"


def contract(name: str, version: str):
    """
    Mark a class as a published cross-service contract.

    Attaches a :class:`ContractMeta` instance to the decorated class as
    ``cls.__contract__``. Returns the class unchanged — pure decoration,
    no wrapping — so Pydantic validation, serialization, and any other
    runtime behaviour are unaffected.

    Works with any class, not just Pydantic ``BaseModel`` subclasses, but
    the intended use is always Pydantic models.

    .. stability: experimental

    Args:
        name:    The contract's stable name.
        version: The contract's version string.

    Returns:
        A decorator that attaches ``__contract__`` to the class and
        returns it unchanged.

    Usage::

        @contract(name="item", version="1.0")
        class Item(BaseModel):
            id: str
            name: str
    """

    def _decorate(cls: type) -> type:
        cls.__contract__ = ContractMeta(name=name, version=version)
        return cls

    return _decorate


contract.__stability__ = "experimental"


def get_contract_meta(cls: type) -> ContractMeta | None:
    """
    Return the ContractMeta attached to a class, if any.

    Safe on any class — undecorated classes simply return ``None``
    rather than raising.

    .. stability: experimental

    Args:
        cls: The class to inspect.

    Returns:
        The :class:`ContractMeta` attached via :func:`contract`, or
        ``None`` if the class is not @contract-decorated.
    """
    return getattr(cls, "__contract__", None)


get_contract_meta.__stability__ = "experimental"
