"""
Shared composition hooks for wiring :class:`~src.composition.BackendApplicationContainer`.

Runtime entrypoints (FastAPI, Streamlit in-process) choose **how** project chain handles are evicted;
the service graph and use cases are always built via :func:`~src.composition.build_backend`.
"""

from __future__ import annotations

from collections.abc import Callable


def process_scoped_chain_invalidate_key() -> Callable[[str], None]:
    """
    Return the process-wide chain-cache drop callable (FastAPI / single worker).

    Uses :class:`~src.infrastructure.caching.process_project_chain_cache.ProcessProjectChainCache`.
    """
    from src.infrastructure.caching.process_project_chain_cache import (
        get_default_process_project_chain_cache,
    )

    return get_default_process_project_chain_cache().drop
