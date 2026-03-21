"""
Top-level Evaluation page tabs: orchestration only, delegates to tab renderers.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from src.ui.evaluation_dataset_tab import render_evaluation_dataset_tab
from src.ui.evaluation_gold_qa_tab import render_evaluation_gold_qa_tab
from src.ui.evaluation_manual_tab import render_evaluation_manual_tab


def render_evaluation_tabs(
    *,
    manual_payload: dict[str, Any],
    dataset_payload: dict[str, Any],
    gold_qa_payload: dict[str, Any],
) -> None:
    tab_manual, tab_dataset, tab_gold = st.tabs(
        ["Manual evaluation", "Dataset evaluation", "Gold QA dataset"]
    )
    with tab_manual:
        render_evaluation_manual_tab(manual_payload)
    with tab_dataset:
        render_evaluation_dataset_tab(dataset_payload)
    with tab_gold:
        render_evaluation_gold_qa_tab(gold_qa_payload)
