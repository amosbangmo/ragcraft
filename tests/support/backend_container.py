"""Test helpers for building a full :class:`~src.composition.BackendApplicationContainer`."""

from __future__ import annotations

from collections.abc import Callable

from src.composition import BackendApplicationContainer, BackendComposition, build_backend, build_backend_composition
from src.application.frontend_support.memory_chat_transcript import MemoryChatTranscript


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
