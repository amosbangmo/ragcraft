"""
Overview tab: curated benchmark summary, charts, and high-level manual preview.
"""

from __future__ import annotations

import streamlit as st

from src.domain.manual_evaluation_result import ManualEvaluationResult
from src.ui.evaluation_overview import render_evaluation_overview
from src.ui.manual_evaluation import render_manual_evaluation_compact


def render_evaluation_overview_tab(
    summary: dict,
    rows: list[dict],
    *,
    manual_result: ManualEvaluationResult | None = None,
) -> None:
    st.markdown("### Analysis workspace")
    st.caption(
        "Use **Overview** for health at a glance, **Questions** to inspect one item, **Debug** for technical "
        "depth, and **Reports** for downloads."
    )

    has_bench = bool(summary or rows)

    if has_bench:
        render_evaluation_overview(summary, rows)
        if manual_result is not None:
            st.markdown("---")
            st.markdown("##### Latest manual run")
            render_manual_evaluation_compact(manual_result)
    elif manual_result is not None:
        st.markdown("### Latest manual run")
        render_manual_evaluation_compact(manual_result)
        st.info(
            "Run **dataset evaluation** (above) to populate aggregate benchmark metrics, charts, and global signals."
        )
    else:
        st.info(
            "Run **dataset evaluation** to see aggregate quality, charts, and global signals here. "
            "Run **manual evaluation** for a single-question preview."
        )
