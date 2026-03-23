from __future__ import annotations

import json
from dataclasses import asdict

import streamlit as st

from services.api_client import (
    BackendClient,
    PRESET_DESCRIPTIONS,
    PRESET_SELECT_ORDER,
    PRESET_UI_LABELS,
    RetrievalPreset,
    RetrievalPresetMergePort,
    RetrievalSettingsPayload,
    default_retrieval_preset_merge_port,
    parse_retrieval_preset,
)
from services.settings_dtos import UpdateProjectRetrievalSettingsCommand

_RETRIEVAL_PANEL_BOUND_PROJECT = "_retrieval_panel_bound_project"

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
    service: RetrievalPresetMergePort | None = None,
) -> RetrievalSettingsPayload:
    """
    Preset-backed settings, optionally merged with advanced toggle overrides.

    Exposed for unit tests (preset mapping and merge behavior).
    """
    svc = service or default_retrieval_preset_merge_port()
    settings = svc.from_preset(preset)
    overrides: dict = {}
    if enable_query_rewrite is not None:
        overrides["enable_query_rewrite"] = bool(enable_query_rewrite)
    if enable_hybrid_retrieval is not None:
        overrides["enable_hybrid_retrieval"] = bool(enable_hybrid_retrieval)
    if overrides:
        return svc.merge(settings, overrides)
    return settings


def retrieval_settings_to_request_dict(settings: RetrievalSettingsPayload) -> dict:
    """Flat dict for chat/search ask endpoints (retrieval override payload)."""
    return dict(asdict(settings))


def _retrieval_persist_signature_key(user_id: str, project_id: str) -> str:
    return f"_retrieval_persist_sig_{user_id}_{project_id}"


def _sync_retrieval_panel_from_backend(
    *,
    user_id: str,
    project_id: str,
    backend_client: BackendClient,
) -> None:
    target = f"{user_id}:{project_id}"
    if st.session_state.get(_RETRIEVAL_PANEL_BOUND_PROJECT) == target:
        return

    view = backend_client.get_effective_retrieval_settings(user_id, project_id)
    ps = view.preferences
    st.session_state["retrieval_preset"] = parse_retrieval_preset(ps.retrieval_preset).value
    st.session_state["retrieval_advanced"] = ps.retrieval_advanced
    if ps.retrieval_advanced:
        st.session_state["retrieval_query_rewrite"] = ps.enable_query_rewrite
        st.session_state["retrieval_hybrid"] = ps.enable_hybrid_retrieval
    else:
        p = parse_retrieval_preset(ps.retrieval_preset)
        rw, hy = _PRESET_DEFAULT_TOGGLES.get(p.value, (True, True))
        st.session_state["retrieval_query_rewrite"] = rw
        st.session_state["retrieval_hybrid"] = hy

    st.session_state[_RETRIEVAL_PANEL_BOUND_PROJECT] = target
    st.session_state[_retrieval_persist_signature_key(user_id, project_id)] = json.dumps(
        [
            st.session_state["retrieval_preset"],
            st.session_state["retrieval_advanced"],
            st.session_state["retrieval_query_rewrite"],
            st.session_state["retrieval_hybrid"],
        ]
    )


def _maybe_persist_retrieval_project_settings(
    *,
    user_id: str,
    project_id: str,
    backend_client: BackendClient,
) -> None:
    sig_key = _retrieval_persist_signature_key(user_id, project_id)
    sig = json.dumps(
        [
            st.session_state["retrieval_preset"],
            st.session_state["retrieval_advanced"],
            st.session_state["retrieval_query_rewrite"],
            st.session_state["retrieval_hybrid"],
        ]
    )
    if st.session_state.get(sig_key) == sig:
        return
    backend_client.update_project_retrieval_settings(
        UpdateProjectRetrievalSettingsCommand(
            user_id=user_id,
            project_id=project_id,
            retrieval_preset=str(st.session_state["retrieval_preset"]),
            retrieval_advanced=bool(st.session_state["retrieval_advanced"]),
            enable_query_rewrite=bool(st.session_state["retrieval_query_rewrite"]),
            enable_hybrid_retrieval=bool(st.session_state["retrieval_hybrid"]),
        )
    )
    st.session_state[sig_key] = sig


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
    service: RetrievalPresetMergePort | None = None,
    user_id: str | None = None,
    project_id: str | None = None,
    backend_client: BackendClient | None = None,
) -> RetrievalSettingsPayload:
    """
    Render retrieval preset (and optional advanced overrides) and persist merged settings.

    Session keys:
    - ``retrieval_preset`` — ``precise`` | ``balanced`` | ``exploratory``
    - ``retrieval_advanced`` — show rewrite / hybrid overrides
    - ``retrieval_query_rewrite`` / ``retrieval_hybrid`` — used when advanced is on
    - ``retrieval_settings`` — merged ``RetrievalSettings`` for backend calls

    When ``user_id``, ``project_id``, and ``backend_client`` are set, loads/saves use
    :meth:`~services.api_client.BackendClient.get_effective_retrieval_settings`
    and
    :meth:`~services.api_client.BackendClient.update_project_retrieval_settings`.
    """
    svc = service or default_retrieval_preset_merge_port()

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

    if user_id and project_id and backend_client is not None:
        _sync_retrieval_panel_from_backend(
            user_id=user_id, project_id=project_id, backend_client=backend_client
        )

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

    if user_id and project_id and backend_client is not None:
        _maybe_persist_retrieval_project_settings(
            user_id=user_id,
            project_id=project_id,
            backend_client=backend_client,
        )

    st.session_state["retrieval_settings"] = settings
    return settings
