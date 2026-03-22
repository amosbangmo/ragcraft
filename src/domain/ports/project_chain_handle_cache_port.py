"""
Port for dropping in-process handles keyed by ``project_id`` (e.g. loaded vector indexes).

Used by :class:`~src.infrastructure.services.vectorstore_service.VectorStoreService` and by application-layer
invalidation so the HTTP API never reaches Streamlit session state.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProjectChainHandleCachePort(Protocol):
    """Backend-only cache of expensive per-project objects; ``drop`` evicts a stale handle."""

    def get(self, project_id: str) -> object | None:
        """Return a cached handle or ``None`` if missing."""

    def set(self, project_id: str, value: object) -> None:
        """Store a handle for the given project id."""

    def drop(self, project_id: str) -> None:
        """Remove the entry so the next load rebuilds from disk."""
