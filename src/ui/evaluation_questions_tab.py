"""
Questions tab: pick one manual or benchmark result and inspect scores vs evidence separately.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from src.domain.manual_evaluation_result import ManualEvaluationResult
from src.ui.evaluation_question_detail import render_benchmark_row_detail
from src.ui.manual_evaluation import render_manual_evaluation_result
from src.ui.raw_assets import render_raw_assets


def render_evaluation_questions_tab(
    *,
    available_questions: list[dict[str, Any]],
    selected_question_payload: dict[str, Any] | None,
) -> None:
    _ = selected_question_payload

    if not available_questions:
        st.info(
            "No evaluation results in this session yet. Run **manual evaluation** or **dataset evaluation** "
            "above, then choose an item here."
        )
        return

    pick_idx = st.selectbox(
        "Inspect question or run",
        options=range(len(available_questions)),
        format_func=lambda i: str(available_questions[i]["label"]),
        key="evaluation_questions_pick_idx",
    )
    choice = available_questions[int(pick_idx)]

    tab_scores, tab_evidence = st.tabs(["Scores", "Evidence"])

    with tab_scores:
        if choice.get("kind") == "manual":
            manual = choice.get("manual_result")
            if not isinstance(manual, ManualEvaluationResult):
                st.warning("Manual evaluation payload is missing.")
            else:
                render_manual_evaluation_result(
                    manual,
                    raw_assets_collapsed=False,
                    include_raw_assets=False,
                )
        else:
            row = choice.get("row")
            if not isinstance(row, dict):
                st.warning("Benchmark row payload is missing.")
            else:
                render_benchmark_row_detail(row, include_full_row_json_expander=False)

    with tab_evidence:
        if choice.get("kind") == "manual":
            manual = choice.get("manual_result")
            if not isinstance(manual, ManualEvaluationResult):
                st.warning("Manual evaluation payload is missing.")
            else:
                st.caption(
                    "Raw text, tables, and images passed into the prompt after reranking."
                )
                render_raw_assets(manual.raw_assets, mode="evaluation")
        else:
            row = choice.get("row")
            if not isinstance(row, dict):
                st.warning("Benchmark row payload is missing.")
            else:
                st.caption("Full benchmark row JSON for this dataset entry.")
                st.json(row)
