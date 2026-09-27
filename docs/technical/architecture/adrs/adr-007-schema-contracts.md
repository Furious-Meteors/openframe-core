# ADR-007 — `@contract` Marker for Cross-Service Schema Governance

**Status:** Accepted — v3.2.1

---

## Context

As the ecosystem grows past a handful of services, the same domain shape
(e.g. an `Item`, an `Artifact`) tends to get redefined independently in
each service that touches it — once as a Postgres row mapping, once as a
Kafka message payload, once as an HTTP response model. Nothing in
`openframe-core` identifies which Pydantic models are *published
contracts* — shapes that cross a service boundary (REST, Kafka, gRPC, or
any other transport) and therefore need governance against breaking
changes — versus purely internal models that are free to change at will.

Governing cross-service contracts (exporting a versioned schema,
diffing two versions for breaking changes, publishing to a registry) is
a substantial, independently-versioned concern with its own dependency
footprint — it does not belong in the platform kernel, which stays
infrastructure-free by design (ADR-002). But *something* has to mark
which models are contracts in the first place, and that marker has to
live somewhere every service can import without pulling in the full
governance machinery.

## Decision

Add a single new module, `openframe.core.schemas`, containing only a
marker — no export logic, no registry, no diffing:

- **`contract(name: str, version: str)`** — a decorator that attaches a
  `ContractMeta(name, version)` instance to the decorated class as
  `cls.__contract__` and returns the class **unchanged**. It does not
  wrap, subclass, or alter validation/serialization behaviour in any
  way — Pydantic (or any other class) is unaffected at runtime.
- **`ContractMeta`** — a plain dataclass carrying `name` and `version`,
  the two fields the downstream diffing tool needs to identify a
  contract independently of its Python class name.
- **`get_contract_meta(cls)`** — a safe accessor returning the attached
  `ContractMeta`, or `None` for any undecorated class.

```python
from openframe.core.schemas import contract

@contract(name="item", version="1.0")
class Item(BaseModel):
    id: str
    name: str
```

The module is deliberately **stdlib-only** — no `pydantic` import, no
`openframe.core` imports from any other module. This keeps `schemas` at
the bottom of the dependency DAG alongside `exceptions`, so decorating a
model never adds a dependency to a service's domain layer, regardless
of whether that service ever installs the governance tooling.

The machinery that *acts* on the marker — schema export to JSON Schema,
a versioned registry, breaking-change diffing, a CI-gateable `check`
command — lives entirely in the separate `openframe-schemas` package
(part of the `openframe-tooling` monorepo), which has its own
dependencies (starting with `pydantic` itself, to introspect the
decorated model) and its own release cadence. `openframe-core` only
ever needs to know that a marker exists and where to read it from.

## Consequences

- **New apex-adjacent module, zero new dependencies.** `openframe.core.schemas`
  joins `exceptions` and `config` as a module importable with no
  transitive dependency beyond the stdlib. Every existing service can
  adopt `@contract` immediately without installing `openframe-schemas`.
- **The decorator is inert without the downstream package.** Decorating
  a model with `@contract` and never installing `openframe-schemas` is
  harmless — `__contract__` sits unused as a class attribute. This is
  intentional: adoption of the marker and adoption of the governance
  tooling are two independent decisions.
- **No enforcement lives in core.** `openframe-core` cannot and does not
  validate that a `name`/`version` pair is unique, well-formed, or
  non-breaking relative to a prior version — all of that is
  `openframe-schemas`' job, by design, so that core's release cadence
  is never coupled to the governance tool's feature set.
- **Stability.** The decorator's signature (`name`, `version`) is
  stable; `ContractMeta` may gain additional fields in a future minor
  version (e.g. an owning team, a deprecation flag) — additive only,
  consistent with the rest of the ecosystem's no-breaking-changes-within-a-major
  policy.

## Alternatives considered

- **Put the marker inside `openframe-schemas` itself**, so services
  that want `@contract` install that package directly. Rejected: this
  would force every service defining a domain model — the overwhelming
  majority of which never touch schema diffing — to add a dependency
  and its transitive footprint just to tag a class. Splitting the inert
  marker from the active tooling means the cost of *marking* a contract
  is zero, and only the cost of *governing* it is opt-in.
- **Use a plain class-level attribute instead of a decorator**
  (`class Item(BaseModel): __contract_name__ = "item"`). Rejected: a
  decorator is more discoverable at the definition site, composes with
  any base class (not just Pydantic), and keeps the marker's shape
  (`ContractMeta`) as a single typed object rather than two
  loosely-related class attributes a reader has to know to look for
  together.

---

*See [`openframe-tooling`](https://github.com/Furious-Meteors/openframe-tooling)'s
`openframe-schemas` package for the export/registry/diff machinery that
reads this marker, and its README's "Breaking-change rules" table for
the compatibility classification `openframe-schemas` applies once a
model is tagged.*
