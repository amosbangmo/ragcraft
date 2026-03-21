"""
Top-level Evaluation page tabs: orchestration only, delegates to tab renderers.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from src.ui.evaluation_debug_tab import render_evaluation_debug_tab
from src.ui.evaluation_overview_tab import render_evaluation_overview_tab
from src.ui.evaluation_questions_tab import render_evaluation_questions_tab
from src.ui.evaluation_reports_tab import render_evaluation_reports_tab


def render_evaluation_tabs(
    *,
    overview_payload: dict[str, Any],
    question_payload: dict[str, Any],
    debug_payload: dict[str, Any],
    reports_payload: dict[str, Any],
) -> None:
    tab_overview, tab_questions, tab_debug, tab_reports = st.tabs(
        ["Overview", "Questions", "Debug", "Reports"]
    )
    with tab_overview:
        render_evaluation_overview_tab(
            summary=overview_payload.get("summary") or {},
            rows=overview_payload.get("rows") or [],
            manual_result=overview_payload.get("manual_result"),
        )
    with tab_questions:
        render_evaluation_questions_tab(
            available_questions=question_payload.get("available_questions") or [],
            selected_question_payload=question_payload.get("selected_question_payload"),
        )
    with tab_debug:
        render_evaluation_debug_tab(debug_payload)
    with tab_reports:
        render_evaluation_reports_tab(reports_payload)
