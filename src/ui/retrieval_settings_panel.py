from __future__ import annotations

from dataclasses import asdict
from typing import Callable

import streamlit as st

from src.domain.retrieval_settings import RetrievalSettings
from src.services.retrieval_settings_service import RetrievalSettingsService

PRESET_PRECISE = "Precise"
PRESET_BALANCED = "Balanced"
PRESET_EXPLORATORY = "Exploratory"

PRESET_OPTIONS: tuple[str, ...] = (PRESET_PRECISE, PRESET_BALANCED, PRESET_EXPLORATORY)

# When the user picks a preset, seed toggles to these defaults (they can still override).
_PRESET_DEFAULT_TOGGLES: dict[str, tuple[bool, bool]] = {
    PRESET_PRECISE: (True, False),
    PRESET_BALANCED: (True, True),
    PRESET_EXPLORATORY: (False, True),
}

_PRECISE_K = 8


def _preset_field_overrides(preset: str) -> Callable[[RetrievalSettings], dict[str, int]]:
    def _precise(_base: RetrievalSettings) -> dict[str, int]:
        return {
            "similarity_search_k": _PRECISE_K,
            "bm25_search_k": _PRECISE_K,
            "hybrid_search_k": _PRECISE_K,
        }

    def _balanced(_base: RetrievalSettings) -> dict[str, int]:
        return {}

    def _exploratory(base: RetrievalSettings) -> dict[str, int]:
        k = max(30, int(base.similarity_search_k * 1.5))
        return {
            "similarity_search_k": k,
            "bm25_search_k": max(base.bm25_search_k, k),
            "hybrid_search_k": max(base.hybrid_search_k, k),
        }

    builders: dict[str, Callable[[RetrievalSettings], dict[str, int]]] = {
        PRESET_PRECISE: _precise,
        PRESET_BALANCED: _balanced,
        PRESET_EXPLORATORY: _exploratory,
    }
    return builders[preset]


def build_ui_retrieval_settings(
    *,
    preset: str,
    enable_query_rewrite: bool,
    enable_hybrid_retrieval: bool,
    service: RetrievalSettingsService | None = None,
) -> RetrievalSettings:
    """
    Merge env-backed defaults with preset k-shaping and user toggles.
    Exposed for unit tests (preset mapping correctness).
    """
    if preset not in _PRESET_DEFAULT_TOGGLES:
        preset = PRESET_BALANCED

    svc = service or RetrievalSettingsService()
    base = svc.get_default()
    overrides: dict = dict(_preset_field_overrides(preset)(base))
    overrides["enable_query_rewrite"] = bool(enable_query_rewrite)
    overrides["enable_hybrid_retrieval"] = bool(enable_hybrid_retrieval)
    return svc.merge(base, overrides)


def retrieval_settings_to_request_dict(settings: RetrievalSettings) -> dict:
    """Flat dict for ``RAGService`` / ``RetrievalSettingsService.merge``."""
    return dict(asdict(settings))


def _on_retrieval_preset_changed() -> None:
    preset = st.session_state.get("retrieval_preset", PRESET_BALANCED)
    rw, hy = _PRESET_DEFAULT_TOGGLES.get(preset, (True, True))
    st.session_state["retrieval_query_rewrite"] = rw
    st.session_state["retrieval_hybrid"] = hy


def render_retrieval_settings_panel(
    *,
    title: str = "Retrieval",
    expanded: bool = False,
    service: RetrievalSettingsService | None = None,
) -> RetrievalSettings:
    """
    Render safe retrieval controls and persist the result in session state.

    Session keys:
    - ``retrieval_preset`` — selected preset label
    - ``retrieval_query_rewrite`` / ``retrieval_hybrid`` — toggle values
    - ``retrieval_settings`` — merged ``RetrievalSettings`` for backend calls
    """
    if "retrieval_preset" not in st.session_state:
        st.session_state["retrieval_preset"] = PRESET_BALANCED
    if "retrieval_query_rewrite" not in st.session_state:
        st.session_state["retrieval_query_rewrite"] = True
    if "retrieval_hybrid" not in st.session_state:
        st.session_state["retrieval_hybrid"] = True

    with st.expander(title, expanded=expanded):
        st.caption(
            "Presets shape how many summaries are considered; toggles control rewrite and "
            "hybrid (semantic + keyword) recall. Advanced scoring parameters stay on server defaults."
        )

        st.selectbox(
            "Retrieval preset",
            options=list(PRESET_OPTIONS),
            key="retrieval_preset",
            on_change=_on_retrieval_preset_changed,
        )

        c1, c2 = st.columns(2)
        with c1:
            st.toggle(
                "Query rewrite",
                key="retrieval_query_rewrite",
                help="Rewrite the question into a retrieval-friendly query before search.",
            )
        with c2:
            st.toggle(
                "Hybrid retrieval",
                key="retrieval_hybrid",
                help="Combine vector search with keyword (BM25) search over summaries.",
            )

    settings = build_ui_retrieval_settings(
        preset=str(st.session_state["retrieval_preset"]),
        enable_query_rewrite=bool(st.session_state["retrieval_query_rewrite"]),
        enable_hybrid_retrieval=bool(st.session_state["retrieval_hybrid"]),
        service=service,
    )
    st.session_state["retrieval_settings"] = settings
    return settings
