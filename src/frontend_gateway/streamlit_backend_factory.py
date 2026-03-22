"""
Build :class:`~src.composition.BackendApplicationContainer` for the Streamlit in-process mode.

Uses the same :func:`~src.composition.build_backend` graph as FastAPI, with a chain-invalidation hook
that clears both the process-scoped cache and Streamlit session chain handles.
"""

from __future__ import annotations

from src.composition import BackendApplicationContainer, build_backend
from src.composition.backend_composition import build_backend_composition
from src.composition.wiring import process_scoped_chain_invalidate_key
from src.frontend_gateway.factories.chat_service_factory import build_chat_service
from src.ui.streamlit_project_chain_session_cache import invalidate_project_chain as _invalidate_streamlit_session_chain


def _invalidate_process_and_streamlit_chain_cache(project_id: str) -> None:
    process_scoped_chain_invalidate_key()(project_id)
    _invalidate_streamlit_session_chain(project_id)


def build_streamlit_backend_application_container() -> BackendApplicationContainer:
    return build_backend(
        invalidate_chain_key=_invalidate_process_and_streamlit_chain_cache,
        backend=build_backend_composition(chat_transcript=build_chat_service()),
    )
