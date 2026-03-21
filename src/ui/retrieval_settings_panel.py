from __future__ import annotations

from dataclasses import asdict

import streamlit as st

from src.domain.retrieval_presets import (
    PRESET_DESCRIPTIONS,
    PRESET_SELECT_ORDER,
    PRESET_UI_LABELS,
    RetrievalPreset,
    parse_retrieval_preset,
)
from src.domain.retrieval_settings import RetrievalSettings
from src.services.retrieval_settings_service import RetrievalSettingsService

# Backward compatibility for tests and imports
PRESET_PRECISE = RetrievalPreset.PRECISE.value
PRESET_BALANCED = RetrievalPreset.BALANCED.value
PRESET_EXPLORATORY = RetrievalPreset.EXPLORATORY.value

PRESET_OPTIONS: tuple[str, ...] = tuple(p.value for p in PRESET_SELECT_ORDER)

_PRESET_DEFAULT_TOGGLES: dict[str, tuple[bool, bool]] = {
    RetrievalPreset.PRECISE.value: (True, False),
    RetrievalPreset.BALANCED.value: (True, True),
    RetrievalPreset.EXPLORATORY.value: (False, True),
}


def _label_for_preset_value(value: str) -> str:
    p = parse_retrieval_preset(value)
    return PRESET_UI_LABELS[p]


def build_ui_retrieval_settings(
    *,
    preset: str,
    enable_query_rewrite: bool | None = None,
    enable_hybrid_retrieval: bool | None = None,
    service: RetrievalSettingsService | None = None,
) -> RetrievalSettings:
    """
    Preset-backed settings, optionally merged with advanced toggle overrides.

    Exposed for unit tests (preset mapping and merge behavior).
    """
    svc = service or RetrievalSettingsService()
    settings = svc.from_preset(preset)
    overrides: dict = {}
    if enable_query_rewrite is not None:
        overrides["enable_query_rewrite"] = bool(enable_query_rewrite)
    if enable_hybrid_retrieval is not None:
        overrides["enable_hybrid_retrieval"] = bool(enable_hybrid_retrieval)
    if overrides:
        return svc.merge(settings, overrides)
    return settings


def retrieval_settings_to_request_dict(settings: RetrievalSettings) -> dict:
    """Flat dict for ``RAGService`` / ``RetrievalSettingsService.merge``."""
    return dict(asdict(settings))


def _on_retrieval_preset_changed() -> None:
    preset = str(st.session_state.get("retrieval_preset", RetrievalPreset.BALANCED.value))
    rw, hy = _PRESET_DEFAULT_TOGGLES.get(
        parse_retrieval_preset(preset).value,
        (True, True),
    )
    st.session_state["retrieval_query_rewrite"] = rw
    st.session_state["retrieval_hybrid"] = hy


def render_retrieval_settings_panel(
    *,
    title: str = "Retrieval",
    expanded: bool = False,
    service: RetrievalSettingsService | None = None,
) -> RetrievalSettings:
    """
    Render retrieval preset (and optional advanced overrides) and persist merged settings.

    Session keys:
    - ``retrieval_preset`` — ``precise`` | ``balanced`` | ``exploratory``
    - ``retrieval_advanced`` — show rewrite / hybrid overrides
    - ``retrieval_query_rewrite`` / ``retrieval_hybrid`` — used when advanced is on
    - ``retrieval_settings`` — merged ``RetrievalSettings`` for backend calls
    """
    svc = service or RetrievalSettingsService()

    if "retrieval_preset" not in st.session_state:
        st.session_state["retrieval_preset"] = RetrievalPreset.BALANCED.value
    else:
        st.session_state["retrieval_preset"] = parse_retrieval_preset(
            st.session_state["retrieval_preset"]
        ).value

    if "retrieval_advanced" not in st.session_state:
        st.session_state["retrieval_advanced"] = False

    if "retrieval_query_rewrite" not in st.session_state:
        st.session_state["retrieval_query_rewrite"] = True
    if "retrieval_hybrid" not in st.session_state:
        st.session_state["retrieval_hybrid"] = True

    with st.expander(title, expanded=expanded):
        st.selectbox(
            "Retrieval preset",
            options=list(PRESET_OPTIONS),
            format_func=_label_for_preset_value,
            key="retrieval_preset",
            on_change=_on_retrieval_preset_changed,
        )

        active = parse_retrieval_preset(st.session_state["retrieval_preset"])
        st.caption(PRESET_DESCRIPTIONS[active])

        st.toggle(
            "Advanced: override query rewrite & hybrid",
            key="retrieval_advanced",
            help="When off, the preset alone defines rewrite, hybrid, and k. When on, the toggles below apply on top of the preset k-shaping.",
        )

        if st.session_state["retrieval_advanced"]:
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

    if st.session_state["retrieval_advanced"]:
        settings = build_ui_retrieval_settings(
            preset=str(st.session_state["retrieval_preset"]),
            enable_query_rewrite=bool(st.session_state["retrieval_query_rewrite"]),
            enable_hybrid_retrieval=bool(st.session_state["retrieval_hybrid"]),
            service=svc,
        )
    else:
        settings = svc.from_preset(str(st.session_state["retrieval_preset"]))

    st.session_state["retrieval_settings"] = settings
    return settings
