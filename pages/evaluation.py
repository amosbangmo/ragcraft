import streamlit as st

from typing import cast
from src.app.ragcraft_app import RAGCraftApp
from src.ui.layout import apply_layout
from src.ui.page_header import render_page_header
from src.ui.raw_assets import render_raw_assets
from src.ui.request_runner import (
    is_request_running,
    run_request_action,
    render_result_payload,
)
from src.ui.source_citations import render_source_citations
from src.auth.guards import require_authentication
from src.core.error_utils import get_user_error_message
from src.core.exceptions import (
    LLMServiceError,
    VectorStoreError,
    DocStoreError,
)


st.set_page_config(
    page_title="Evaluation | RAGCraft",
    page_icon="📊",
    layout="wide",
)

require_authentication("pages/evaluation.py")
apply_layout()

EVALUATION_REQUEST_KEY = "evaluation_request_running"
EVALUATION_RESULT_KEY = "evaluation_result_payload"


header = render_page_header(
    badge="Evaluation",
    title="Test answer quality",
    subtitle="Run evaluation queries and inspect the raw evidence used to generate the answer.",
    selector_label="Project for evaluation",
)

app = cast(RAGCraftApp, header["app"])
user_id = str(header["user_id"])
project_id = str(header["project_id"]) if header["project_id"] else None

if not project_id:
    st.stop()

question = st.text_input("Evaluation question", placeholder="Enter a test question...")


def _run_evaluation():
    return app.ask_question(
        user_id=user_id,
        project_id=project_id,
        question=question,
        chat_history=[],
    )


def _map_evaluation_error(exc: Exception) -> str:
    if isinstance(exc, VectorStoreError):
        return get_user_error_message(exc, "Unable to query the FAISS index for this evaluation.")
    if isinstance(exc, DocStoreError):
        return get_user_error_message(exc, "Unable to retrieve supporting assets from SQLite.")
    if isinstance(exc, LLMServiceError):
        return get_user_error_message(exc, "The language model failed while generating the evaluation answer.")
    return get_user_error_message(exc, f"Unexpected error while running evaluation: {exc}")


def _render_evaluation_result(response):
    if response is None:
        st.warning("No RAG response available.")
        return

    c1, c2 = st.columns([3, 1])

    with c1:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Answer</div>', unsafe_allow_html=True)
        st.write(response.answer)
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.metric("Confidence", response.confidence)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Source citations</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="card-subtitle">Structured citation layer generated from the raw retrieved assets.</div>',
        unsafe_allow_html=True,
    )
    render_source_citations(getattr(response, "citations", []))
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Raw evidence used</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="card-subtitle">Review the raw text, tables, and extracted images selected after summary retrieval.</div>',
        unsafe_allow_html=True,
    )
    render_raw_assets(
        response.raw_assets,
        mode="evaluation",
    )
    st.markdown("</div>", unsafe_allow_html=True)


run_clicked = st.button(
    "Run evaluation",
    use_container_width=True,
    disabled=is_request_running(EVALUATION_REQUEST_KEY),
)

if run_clicked and not question.strip():
    st.warning("Please enter an evaluation question.")
else:
    run_request_action(
        request_key=EVALUATION_REQUEST_KEY,
        result_key=EVALUATION_RESULT_KEY,
        trigger=run_clicked,
        can_run=bool(question.strip()),
        action=_run_evaluation,
        spinner_text="Running evaluation...",
        error_mapper=_map_evaluation_error,
    )

render_result_payload(
    result_key=EVALUATION_RESULT_KEY,
    on_success=_render_evaluation_result,
)
