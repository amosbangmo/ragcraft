"""
Build :class:`~src.composition.BackendApplicationContainer` for the Streamlit process.

Uses the same :func:`~src.composition.build_backend` graph as FastAPI, with a chain-invalidation hook
that clears both the process-scoped cache and Streamlit session chain handles.
"""

from __future__ import annotations

from src.composition import BackendApplicationContainer, build_backend, build_backend_composition
from src.infrastructure.caching.process_project_chain_cache import get_default_process_project_chain_cache
from src.ui.streamlit_project_chain_session_cache import invalidate_project_chain as _invalidate_streamlit_session_chain


def _invalidate_process_and_streamlit_chain_cache(project_id: str) -> None:
    get_default_process_project_chain_cache().drop(project_id)
    _invalidate_streamlit_session_chain(project_id)


def build_streamlit_backend_application_container() -> BackendApplicationContainer:
    return build_backend(
        backend=build_backend_composition(),
        invalidate_chain_key=_invalidate_process_and_streamlit_chain_cache,
    )
