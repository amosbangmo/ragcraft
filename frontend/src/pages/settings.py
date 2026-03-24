"""
Project-level retrieval defaults (preset + advanced overrides).

Uses :func:`components.shared.retrieval_settings_panel.render_retrieval_settings_panel` so changes
persist via :meth:`services.api_client.BackendClient.update_project_retrieval_settings`.
"""

from __future__ import annotations

import streamlit as st

from components.shared.layout import apply_layout
from components.shared.page_header import render_page_header
from components.shared.retrieval_settings_panel import render_retrieval_settings_panel
from infrastructure.auth.guards import require_authentication
from services.api_client import BackendClient
from services.settings_dtos import UpdateProjectRetrievalSettingsCommand

st.set_page_config(
    page_title="Settings | RAGCraft",
    page_icon="⚙️",
    layout="wide",
)

require_authentication("pages/settings.py")
apply_layout()

st.markdown('<div data-testid="settings-page-root"></div>', unsafe_allow_html=True)

header = render_page_header(
    badge="Settings",
    title="Retrieval defaults",
    subtitle="Preset and overrides apply to the active project and are shared across Chat, Search, and Evaluation.",
    show_project_selector=True,
)

client: BackendClient = header["backend_client"]
user_id = str(header["user_id"])
project_id = header["project_id"]

if not project_id:
    st.warning("Select a project in the header to edit retrieval defaults.")
    st.stop()

render_retrieval_settings_panel(
    title="Project retrieval settings",
    expanded=True,
    user_id=user_id,
    project_id=str(project_id),
    backend_client=client,
)

st.markdown('<div data-testid="retrieval-save-button"></div>', unsafe_allow_html=True)
if st.button("Save retrieval defaults", key="e2e_retrieval_save_defaults"):
    client.update_project_retrieval_settings(
        UpdateProjectRetrievalSettingsCommand(
            user_id=user_id,
            project_id=str(project_id),
            retrieval_preset=str(st.session_state["retrieval_preset"]),
            retrieval_advanced=bool(st.session_state["retrieval_advanced"]),
            enable_query_rewrite=bool(st.session_state["retrieval_query_rewrite"]),
            enable_hybrid_retrieval=bool(st.session_state["retrieval_hybrid"]),
        )
    )
    st.markdown(
        '<div data-testid="retrieval-settings-success-banner"></div>', unsafe_allow_html=True
    )
    st.success("Retrieval defaults saved.")
