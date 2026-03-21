"""
Top-level Evaluation page tabs: orchestration only, delegates to tab renderers.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from src.ui.evaluation_dataset_tab import render_evaluation_dataset_tab
from src.ui.evaluation_gold_qa_tab import render_evaluation_gold_qa_tab
from src.ui.evaluation_manual_tab import render_evaluation_manual_tab
from src.ui.evaluation_retrieval_tab import render_evaluation_retrieval_tab


def render_evaluation_tabs(
    *,
    manual_payload: dict[str, Any],
    dataset_payload: dict[str, Any],
    gold_qa_payload: dict[str, Any],
    retrieval_payload: dict[str, Any],
) -> None:
    tab_manual, tab_dataset, tab_gold, tab_retrieval = st.tabs(
        ["Manual evaluation", "Dataset evaluation", "Gold QA dataset", "Retrieval analytics"]
    )
    with tab_manual:
        render_evaluation_manual_tab(manual_payload)
    with tab_dataset:
        render_evaluation_dataset_tab(dataset_payload)
    with tab_gold:
        render_evaluation_gold_qa_tab(gold_qa_payload)
    with tab_retrieval:
        render_evaluation_retrieval_tab(retrieval_payload)
