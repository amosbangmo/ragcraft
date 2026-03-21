"""
Manual evaluation tab: single-question workflow and structured quality breakdown.
"""

from __future__ import annotations

from typing import Any, cast

import streamlit as st

from src.app.ragcraft_app import RAGCraftApp
from src.core.error_utils import get_user_error_message
from src.core.exceptions import DocStoreError, LLMServiceError, VectorStoreError
from src.domain.manual_evaluation_result import ManualEvaluationResult, is_manual_evaluation_result_like
from src.ui.manual_evaluation import render_manual_evaluation_result
from src.ui.request_runner import is_request_running, render_result_payload, run_request_action

_MANUAL_QUESTION_KEY = "manual_eval_question"


def parse_evaluation_csv_list(raw_value: str) -> list[str]:
    if not raw_value.strip():
        return []

    values: list[str] = []
    seen: set[str] = set()

    for part in raw_value.split(","):
        cleaned = part.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        values.append(cleaned)

    return values


def render_evaluation_manual_tab(payload: dict[str, Any]) -> None:
    app = cast(RAGCraftApp, payload["app"])
    user_id = str(payload["user_id"])
    project_id = str(payload["project_id"])
    evaluation_request_key = str(payload["evaluation_request_key"])
    evaluation_result_key = str(payload["evaluation_result_key"])

    st.caption(
        "Inspect one question interactively: run the pipeline, then review answer quality, citations, "
        "retrieval, and issues. Raw evidence stays collapsed unless you expand it."
    )

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Manual evaluation</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="card-subtitle">Run a single question with optional gold expectations for this run only.</div>',
        unsafe_allow_html=True,
    )

    st.text_input(
        "Evaluation question",
        placeholder="Enter a test question...",
        key=_MANUAL_QUESTION_KEY,
    )

    st.markdown("##### Optional expectations (for this run only)")
    st.caption(
        "These values are not saved to the gold QA dataset. Use them to score retrieval, citations, "
        "and answer overlap locally."
    )
    manual_expected_answer = st.text_area(
        "Expected answer (optional)",
        placeholder="Reference answer for token overlap and exact-match metrics.",
        height=100,
        key="manual_eval_expected_answer",
    )
    col_me1, col_me2 = st.columns(2)
    with col_me1:
        manual_expected_doc_ids = st.text_input(
            "Expected doc_ids (optional, comma-separated)",
            placeholder="doc_1, doc_2",
            key="manual_eval_expected_doc_ids",
        )
    with col_me2:
        manual_expected_sources = st.text_input(
            "Expected source files (optional, comma-separated)",
            placeholder="report.pdf, notes.txt",
            key="manual_eval_expected_sources",
        )

    def _current_question() -> str:
        return str(st.session_state.get(_MANUAL_QUESTION_KEY) or "")

    def _run_evaluation():
        return app.evaluate_manual_question(
            user_id=user_id,
            project_id=project_id,
            question=_current_question(),
            expected_answer=manual_expected_answer.strip() or None,
            expected_doc_ids=parse_evaluation_csv_list(manual_expected_doc_ids),
            expected_sources=parse_evaluation_csv_list(manual_expected_sources),
        )

    def _map_evaluation_error(exc: Exception) -> str:
        if isinstance(exc, VectorStoreError):
            return get_user_error_message(exc, "Unable to query the FAISS index for this evaluation.")
        if isinstance(exc, DocStoreError):
            return get_user_error_message(exc, "Unable to retrieve supporting assets from SQLite.")
        if isinstance(exc, LLMServiceError):
            return get_user_error_message(
                exc, "The language model failed while generating the evaluation answer."
            )
        return get_user_error_message(exc, f"Unexpected error while running evaluation: {exc}")

    run_clicked = st.button(
        "Run evaluation",
        use_container_width=True,
        disabled=is_request_running(evaluation_request_key),
    )

    q_stripped = _current_question().strip()
    if run_clicked and not q_stripped:
        st.warning("Please enter an evaluation question.")
    else:
        run_request_action(
            request_key=evaluation_request_key,
            result_key=evaluation_result_key,
            trigger=run_clicked,
            can_run=bool(q_stripped),
            action=_run_evaluation,
            spinner_text="Running evaluation...",
            error_mapper=_map_evaluation_error,
        )

    st.markdown("</div>", unsafe_allow_html=True)

    def _on_success(result: Any) -> None:
        if is_manual_evaluation_result_like(result):
            render_manual_evaluation_result(
                cast(ManualEvaluationResult, result),
                raw_assets_collapsed=True,
                include_raw_assets=True,
            )
            return
        if isinstance(result, dict) and "error" not in result and "answer" in result:
            st.warning(
                "Result arrived as serialized data; showing a simplified view. "
                "Reload the page if structured metrics are missing."
            )
            st.markdown("##### Answer")
            st.write(result.get("answer") or "—")
            with st.expander("Full payload (JSON)", expanded=False):
                st.json(result)
            return
        st.caption(f"Unexpected evaluation payload (type: {type(result).__name__}).")

    st.markdown("##### Results")
    render_result_payload(
        result_key=evaluation_result_key,
        on_success=_on_success,
    )
