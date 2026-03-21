"""
Analysis tab: exports, advanced benchmark analytics, and technical manual-run payloads.
"""

from __future__ import annotations

from typing import Any, cast

import streamlit as st

from src.domain.manual_evaluation_result import ManualEvaluationResult, is_manual_evaluation_result_like
from src.ui.evaluation_dashboard import render_evaluation_dashboard
from src.ui.evaluation_reports_tab import render_evaluation_reports_tab
from src.ui.raw_assets import render_raw_assets


def render_evaluation_analysis_tab(payload: dict[str, Any]) -> None:
    reports_export = payload.get("reports_export")
    manual_result = payload.get("manual_result")
    summary = cast(dict[str, Any], payload.get("summary") or {})
    rows = cast(list[dict[str, Any]], payload.get("rows") or [])

    st.caption(
        "Exports and deep analytics: downloads from the latest dataset benchmark, full metric dashboards, "
        "distributions, and raw technical payloads when you need them."
    )

    render_evaluation_reports_tab({"export": reports_export})

    st.markdown("---")
    st.markdown("### Advanced evaluation dashboard")
    if summary or rows:
        render_evaluation_dashboard(summary, rows, widget_key_prefix="analysis_eval_dashboard")
        with st.expander("Benchmark summary JSON", expanded=False):
            st.json(summary)
    else:
        st.info(
            "Run **dataset evaluation** under **Dataset evaluation → Metrics** to populate charts, tables, "
            "and comparative views."
        )

    manual = (
        cast(ManualEvaluationResult, manual_result)
        if is_manual_evaluation_result_like(manual_result)
        else None
    )
    if manual is not None:
        st.markdown("---")
        st.markdown("### Manual evaluation (technical)")
        st.caption("Structured JSON and raw evidence for the latest manual run in this session.")
        with st.expander("Manual evaluation JSON", expanded=False):
            st.json(manual.to_dict())
        with st.expander("Raw evidence (full)", expanded=False):
            render_raw_assets(manual.raw_assets, mode="evaluation")
