"""
Central Streamlit ``st.session_state`` keys used across pages.

Keeping string literals here avoids typos and documents the shared session contract.
"""

from __future__ import annotations

# Active workspace (mirrors sidebar / navigation)
PROJECT_ID = "project_id"

# Populated by :func:`components.shared.retrieval_settings_panel.render_retrieval_settings_panel`
RETRIEVAL_SETTINGS = "retrieval_settings"
