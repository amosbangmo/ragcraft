import streamlit as st

from typing import cast
from src.app.ragcraft_app import RAGCraftApp
from src.auth.guards import require_authentication
from src.core.error_utils import get_user_error_message
from src.core.exceptions import DocStoreError, LLMServiceError, VectorStoreError
from src.ui.layout import apply_layout
from src.ui.page_header import render_page_header
from src.ui.request_runner import (
    is_request_running,
    run_request_action,
    render_result_payload,
)


st.set_page_config(
    page_title="Retrieval Comparison | RAGCraft",
    page_icon="⚖️",
    layout="wide",
)

require_authentication("pages/retrieval_comparison.py")
apply_layout()

COMPARISON_REQUEST_KEY = "retrieval_comparison_request_running"
COMPARISON_RESULT_KEY = "retrieval_comparison_result_payload"


def _parse_questions(raw_text: str) -> list[str]:
    return [line.strip() for line in raw_text.splitlines() if line.strip()]


header = render_page_header(
    badge="Retrieval Comparison",
    title="Compare FAISS only vs Hybrid retrieval",
    subtitle="Run a portfolio-grade comparison across multiple questions and inspect recall, confidence and latency deltas.",
    selector_label="Project for retrieval comparison",
)

app = cast(RAGCraftApp, header["app"])
user_id = str(header["user_id"])
project_id = str(header["project_id"]) if header["project_id"] else None

if not project_id:
    st.stop()

questions_text = st.text_area(
    "Evaluation questions (one question per line)",
    height=220,
    placeholder=(
        "What is the main objective of the project?\n"
        "Which metrics are reported in the final table?\n"
        "What does the architecture diagram show?"
    ),
)

enable_query_rewrite = st.toggle(
    "Enable query rewrite for both modes",
    value=True,
    help="Keep the rewrite setting identical across FAISS and Hybrid so the comparison isolates retrieval mode.",
)

questions = _parse_questions(questions_text)


def _run_comparison():
    return app.compare_retrieval_modes(
        user_id=user_id,
        project_id=project_id,
        questions=questions,
        enable_query_rewrite=enable_query_rewrite,
    )


def _map_comparison_error(exc: Exception) -> str:
    if isinstance(exc, VectorStoreError):
        return get_user_error_message(exc, "Unable to query the FAISS index for this comparison.")
    if isinstance(exc, DocStoreError):
        return get_user_error_message(exc, "Unable to inspect project assets from SQLite.")
    if isinstance(exc, LLMServiceError):
        return get_user_error_message(exc, "The language model failed while rewriting one or more retrieval queries.")
    return get_user_error_message(exc, f"Unexpected error while running the comparison: {exc}")


def _render_comparison_result(comparison):
    if comparison is None:
        st.warning("No comparison result available.")
        return

    summary = comparison["summary"]
    rows = comparison["rows"]

    st.markdown("### Comparison summary")

    top_metrics = st.columns(6)
    with top_metrics[0]:
        st.metric("Questions", summary["total_questions"])
    with top_metrics[1]:
        st.metric("Rewrite", "On" if summary["query_rewrite_enabled"] else "Off")
    with top_metrics[2]:
        st.metric("Avg FAISS recall doc_ids", summary["avg_faiss_recall_doc_ids"])
    with top_metrics[3]:
        st.metric("Avg Hybrid recall doc_ids", summary["avg_hybrid_recall_doc_ids"])
    with top_metrics[4]:
        st.metric("Avg FAISS confidence", summary["avg_faiss_confidence"])
    with top_metrics[5]:
        st.metric("Avg Hybrid confidence", summary["avg_hybrid_confidence"])

    second_metrics = st.columns(6)
    with second_metrics[0]:
        st.metric("Avg FAISS latency (ms)", summary["avg_faiss_latency_ms"])
    with second_metrics[1]:
        st.metric("Avg Hybrid latency (ms)", summary["avg_hybrid_latency_ms"])
    with second_metrics[2]:
        st.metric("Hybrid wins on recall", summary["hybrid_wins_on_recall_doc_ids"])
    with second_metrics[3]:
        st.metric("Hybrid wins on confidence", summary["hybrid_wins_on_confidence"])
    with second_metrics[4]:
        st.metric("Avg FAISS prompt assets", summary["avg_faiss_prompt_assets"])
    with second_metrics[5]:
        st.metric("Avg Hybrid prompt assets", summary["avg_hybrid_prompt_assets"])

    st.markdown("### Per-question comparison")
    st.dataframe(rows, use_container_width=True)

    st.markdown("### Portfolio takeaways")

    recall_delta = round(
        summary["avg_hybrid_recall_doc_ids"] - summary["avg_faiss_recall_doc_ids"],
        2,
    )
    confidence_delta = round(
        summary["avg_hybrid_confidence"] - summary["avg_faiss_confidence"],
        2,
    )
    latency_delta = round(
        summary["avg_hybrid_latency_ms"] - summary["avg_faiss_latency_ms"],
        2,
    )

    st.markdown(
        f"""
- **Recall delta:** Hybrid retrieves on average **{recall_delta:+.2f} doc_ids** versus FAISS only.
- **Confidence delta:** Hybrid changes confidence by **{confidence_delta:+.2f}** on average.
- **Latency delta:** Hybrid adds **{latency_delta:+.2f} ms** on average compared with FAISS only.
- **Hybrid recall wins:** {summary["hybrid_wins_on_recall_doc_ids"]}/{summary["total_questions"]} question(s).
- **Hybrid confidence wins:** {summary["hybrid_wins_on_confidence"]}/{summary["total_questions"]} question(s).
"""
    )


run_clicked = st.button(
    "Run FAISS vs Hybrid comparison",
    use_container_width=True,
    disabled=is_request_running(COMPARISON_REQUEST_KEY),
)

if run_clicked and not questions:
    st.warning("Please enter at least one evaluation question.")
else:
    run_request_action(
        request_key=COMPARISON_REQUEST_KEY,
        result_key=COMPARISON_RESULT_KEY,
        trigger=run_clicked,
        can_run=bool(questions),
        action=_run_comparison,
        spinner_text="Running FAISS vs Hybrid comparison...",
        error_mapper=_map_comparison_error,
    )

render_result_payload(
    result_key=COMPARISON_RESULT_KEY,
    on_success=_render_comparison_result,
)
