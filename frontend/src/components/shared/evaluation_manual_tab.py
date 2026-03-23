"""
Manual evaluation tab: single-question workflow and structured quality breakdown.
"""

from __future__ import annotations

from typing import Any, cast

import streamlit as st

from services.protocol import BackendClient
from services.ui_errors import map_evaluation_flow_exception
from services.view_models import ManualEvaluationResult, is_manual_evaluation_result_like
from components.shared.evaluation_csv_utils import parse_evaluation_csv_list
from components.shared.manual_evaluation import render_manual_evaluation_result
from components.shared.raw_assets import render_raw_assets
from components.shared.request_runner import (
    RUNNER_ERROR_KEY,
    get_session_payload,
    is_request_running,
    is_runner_error_payload,
    render_result_payload,
    run_request_action,
)


def render_evaluation_manual_tab(payload: dict[str, Any]) -> None:
    backend_client = cast(BackendClient, payload["backend_client"])
    user_id = str(payload["user_id"])
    project_id = str(payload["project_id"])
    wk = str(payload["widget_key_suffix"])
    evaluation_request_key = str(payload["evaluation_request_key"])
    evaluation_result_key = str(payload["evaluation_result_key"])
    q_key = f"manual_eval_question_{wk}"

    st.caption(
        "Inspect one question interactively: run the pipeline, then review answer quality, prompt sources, "
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
        key=q_key,
    )

    st.markdown("##### Optional expectations (for this run only)")
    st.caption(
        "These values are not saved to the gold QA dataset. Use them to score retrieval, prompt sources, "
        "and answer overlap locally."
    )
    manual_expected_answer = st.text_area(
        "Expected answer (optional)",
        placeholder="Reference answer for token overlap and exact-match metrics.",
        height=100,
        key=f"manual_eval_expected_answer_{wk}",
    )
    col_me1, col_me2 = st.columns(2)
    with col_me1:
        manual_expected_doc_ids = st.text_input(
            "Expected doc_ids (optional, comma-separated)",
            placeholder="doc_1, doc_2",
            key=f"manual_eval_expected_doc_ids_{wk}",
        )
    with col_me2:
        manual_expected_sources = st.text_input(
            "Expected source files (optional, comma-separated)",
            placeholder="report.pdf, notes.txt",
            key=f"manual_eval_expected_sources_{wk}",
        )

    def _current_question() -> str:
        return str(st.session_state.get(q_key) or "")

    def _run_evaluation():
        return backend_client.evaluate_manual_question(
            user_id=user_id,
            project_id=project_id,
            question=_current_question(),
            expected_answer=manual_expected_answer.strip() or None,
            expected_doc_ids=parse_evaluation_csv_list(manual_expected_doc_ids),
            expected_sources=parse_evaluation_csv_list(manual_expected_sources),
        )

    def _map_evaluation_error(exc: Exception) -> str:
        return map_evaluation_flow_exception(exc, dataset_evaluation=False)

    run_clicked = st.button(
        "Run evaluation",
        use_container_width=True,
        disabled=is_request_running(evaluation_request_key),
        key=f"manual_eval_run_{wk}",
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
        if isinstance(result, dict) and RUNNER_ERROR_KEY not in result and "answer" in result:
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

    manual_raw = get_session_payload(evaluation_result_key)
    if is_runner_error_payload(manual_raw) or manual_raw is None:
        return
    if is_manual_evaluation_result_like(manual_raw):
        manual = cast(ManualEvaluationResult, manual_raw)
        st.markdown("---")
        st.markdown("##### Manual evaluation (technical)")
        st.caption("Structured JSON and raw evidence for the latest manual run in this session.")
        with st.expander("Manual evaluation JSON", expanded=False):
            st.json(manual.to_dict())
        with st.expander("Raw evidence (full)", expanded=False):
            render_raw_assets(manual.raw_assets, mode="evaluation")
