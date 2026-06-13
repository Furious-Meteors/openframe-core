"""
openframe/core/health/protocol.py
====================================
Health check port for all OpenFrame adapter packages.

Every adapter implements ``HealthCheck`` so the application layer can verify
adapter liveness and readiness without knowing which adapter is wired in.

Two levels of check:
- ``ping()`` — cheap liveness. Used by load balancers and watchdogs. Should
  complete in milliseconds (TCP connect, ``SELECT 1``).
- ``is_ready()`` — full readiness. Used at startup. More expensive — verifies
  schema migrations applied, connection pool healthy, etc.

Runtime isinstance check::

    isinstance(adapter, HealthCheck)   # ✓ works
    isinstance(obj, HealthCheck)       # checks for ping and is_ready methods

Dependency order: this module imports only from Python stdlib typing.
No openframe.core imports.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

__all__ = ["HealthCheck"]


@runtime_checkable
class HealthCheck(Protocol):
    """
    Health check port. Every adapter implements ``ping()`` and ``is_ready()``.

    Adapters satisfy this protocol structurally — no inheritance needed.
    Any class with both async method signatures satisfies ``HealthCheck``.

    ``ping()`` vs ``is_ready()``:

    - ``ping()`` is a low-cost liveness check. Verify a TCP connection can be
      opened, or run ``SELECT 1``. Should complete within milliseconds.
      Called frequently by load balancers and watchdog processes.

    - ``is_ready()`` is a full readiness check. Verify the connection pool is
      healthy, required schemas exist, pending migrations have been applied,
      etc. More expensive — called once at application startup and on
      scheduled readiness probes.

    Usage::

        class PostgresRepository:
            async def ping(self) -> bool:
                try:
                    await self._pool.fetchval("SELECT 1")
                    return True
                except Exception:
                    return False

            async def is_ready(self) -> bool:
                try:
                    await self._pool.fetchval("SELECT COUNT(*) FROM pg_tables")
                    return True
                except Exception:
                    return False

        assert isinstance(PostgresRepository(), HealthCheck)
    """

    async def ping(self) -> bool:
        """
        Low-cost liveness check.

        Verify the adapter can reach its backend. Should be fast and cheap —
        a TCP connect attempt or ``SELECT 1`` is appropriate.

        Returns:
            True if the backend is reachable, False otherwise.
            Must not raise — return False on any failure.
        """
        ...

    async def is_ready(self) -> bool:
        """
        Full readiness check.

        Verify the adapter is fully ready to serve requests. More thorough
        than ``ping()`` — check that the schema is correct, migrations are
        applied, and the connection pool has healthy connections.

        Returns:
            True if the adapter is ready to serve, False otherwise.
            Must not raise — return False on any failure.
        """
        ...
