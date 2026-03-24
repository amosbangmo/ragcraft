"""Test helpers for building a full :class:`~composition.BackendApplicationContainer`."""

from __future__ import annotations

from collections.abc import Callable

from application.services.memory_chat_transcript import MemoryChatTranscript
from composition import (
    BackendApplicationContainer,
    BackendComposition,
    build_backend,
    build_backend_composition,
)


def noop_chain_invalidate(_project_id: str) -> None:
    """No-op RAG chain eviction for tests that do not exercise vector handle caches."""


def build_backend_container_for_tests(
    *,
    invalidate_chain_key: Callable[[str], None] | None = None,
    backend: BackendComposition | None = None,
) -> BackendApplicationContainer:
    """
    Single test entrypoint for the application container (same graph as production, configurable hook).

    Prefer this over ad hoc ``build_backend(...)`` calls with duplicated no-op lambdas.
    """
    resolved_backend = backend or build_backend_composition(chat_transcript=MemoryChatTranscript())
    return build_backend(
        invalidate_chain_key=invalidate_chain_key or noop_chain_invalidate,
        backend=resolved_backend,
    )


def build_streamlit_session_aware_backend_container_for_tests() -> BackendApplicationContainer:
    """
    Same composition graph as production, with Streamlit session chain eviction hooks.

    **Tests and E2E only** — not imported by the Streamlit UI. The product UI uses HTTP only
    (:class:`~services.backend.http_backend_client.HttpBackendClient`).
    """
    from components.shared.streamlit_project_chain_session_cache import (
        invalidate_project_chain as _invalidate_streamlit_session_chain,
    )
    from composition.wiring import process_scoped_chain_invalidate_key
    from services.factories.chat_service_factory import build_chat_service

    def _invalidate_process_and_streamlit_chain_cache(project_id: str) -> None:
        process_scoped_chain_invalidate_key()(project_id)
        _invalidate_streamlit_session_chain(project_id)

    return build_backend(
        invalidate_chain_key=_invalidate_process_and_streamlit_chain_cache,
        backend=build_backend_composition(chat_transcript=build_chat_service()),
    )
