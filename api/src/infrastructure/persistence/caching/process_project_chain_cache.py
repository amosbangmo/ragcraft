"""
Thread-safe, process-wide cache for loaded vector-store handles (keyed by ``project_id``).

FastAPI and headless workers share this default instance so
``POST .../retrieval-cache/invalidate`` evicts stale FAISS objects after on-disk index updates.
Streamlit UIs that run in the same process should call :func:`drop` as part of their own
invalidation path (see :mod:`components.shared.streamlit_project_chain_session_cache`).
"""

from __future__ import annotations

import threading
from typing import Any

# Single process-wide cache; tests may reset via ``reset_default_process_project_chain_cache_for_tests``.
_default_cache: ProcessProjectChainCache | None = None
_default_lock = threading.Lock()


class ProcessProjectChainCache:
    """Concrete :class:`~domain.common.ports.project_chain_handle_cache_port.ProjectChainHandleCachePort`."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: dict[str, Any] = {}

    def get(self, project_id: str) -> object | None:
        with self._lock:
            return self._data.get(project_id)

    def set(self, project_id: str, value: object) -> None:
        with self._lock:
            self._data[project_id] = value

    def drop(self, project_id: str) -> None:
        with self._lock:
            self._data.pop(project_id, None)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


def get_default_process_project_chain_cache() -> ProcessProjectChainCache:
    """Lazily construct the shared process cache (one instance per interpreter)."""
    global _default_cache
    with _default_lock:
        if _default_cache is None:
            _default_cache = ProcessProjectChainCache()
        return _default_cache


def reset_default_process_project_chain_cache_for_tests() -> None:
    """Clear and drop the module singleton (unit tests only)."""
    global _default_cache
    with _default_lock:
        if _default_cache is not None:
            _default_cache.clear()
        _default_cache = None
