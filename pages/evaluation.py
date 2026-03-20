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
DATASET_GENERATION_REQUEST_KEY = "dataset_generation_request_running"
DATASET_GENERATION_RESULT_KEY = "dataset_generation_result_payload"
DATASET_EVALUATION_REQUEST_KEY = "dataset_evaluation_request_running"
DATASET_EVALUATION_RESULT_KEY = "dataset_evaluation_result_payload"


def _parse_csv_list(raw_value: str) -> list[str]:
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


header = render_page_header(
    badge="Evaluation",
    title="Test answer quality",
    subtitle="Run manual evaluation queries, manage a gold QA dataset, and compute retrieval metrics for the current project.",
    selector_label="Project for evaluation",
)

app = cast(RAGCraftApp, header["app"])
user_id = str(header["user_id"])
project_id = str(header["project_id"]) if header["project_id"] else None

if not project_id:
    st.stop()

project_documents = app.list_project_documents(user_id, project_id)

if "qa_dataset_success_message" in st.session_state:
    st.success(st.session_state.pop("qa_dataset_success_message"))

if "qa_dataset_error_message" in st.session_state:
    st.error(st.session_state.pop("qa_dataset_error_message"))

st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<div class="card-title">Manual evaluation</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="card-subtitle">Run a single question and inspect the answer, citations, and raw evidence.</div>',
    unsafe_allow_html=True,
)

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

st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<div class="card-title">Gold QA dataset</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="card-subtitle">Add project-specific benchmark questions manually or generate them automatically from indexed assets.</div>',
    unsafe_allow_html=True,
)

st.markdown("### Generate entries automatically")

generation_col1, generation_col2 = st.columns(2)
with generation_col1:
    generation_num_questions = st.number_input(
        "Number of questions to generate",
        min_value=1,
        max_value=20,
        value=5,
        step=1,
    )

with generation_col2:
    generation_selected_files = st.multiselect(
        "Restrict generation to selected source files (optional)",
        options=project_documents,
        default=[],
        help="Leave empty to use all project documents.",
    )

generation_mode = st.radio(
    "Generation mode",
    options=["append", "replace", "append_dedup"],
    format_func=lambda mode: {
        "append": "Append",
        "replace": "Replace dataset",
        "append_dedup": "Append with dedup",
    }[mode],
    horizontal=True,
    help=(
        "Append: keep existing entries and add new ones. "
        "Replace dataset: delete all existing entries before inserting new ones. "
        "Append with dedup: keep existing entries and skip generated questions already present."
    ),
)


def _run_dataset_generation():
    return app.generate_qa_dataset_entries(
        user_id=user_id,
        project_id=project_id,
        num_questions=int(generation_num_questions),
        source_files=generation_selected_files or None,
        generation_mode=generation_mode,
    )


def _map_dataset_generation_error(exc: Exception) -> str:
    if isinstance(exc, DocStoreError):
        return get_user_error_message(exc, "Unable to inspect indexed assets while generating QA entries.")
    if isinstance(exc, LLMServiceError):
        return get_user_error_message(exc, "The language model failed while generating QA dataset entries.")
    return get_user_error_message(exc, f"Unexpected error while generating QA dataset entries: {exc}")


def _render_dataset_generation_result(payload: dict):
    created_entries = payload["created_entries"]
    skipped_duplicates = payload["skipped_duplicates"]
    deleted_existing_entries = payload["deleted_existing_entries"]
    mode = payload["generation_mode"]

    if mode == "replace":
        st.success(
            f"Dataset replaced successfully: {deleted_existing_entries} existing entr"
            f"{'y' if deleted_existing_entries == 1 else 'ies'} removed and "
            f"{len(created_entries)} new entr{'y' if len(created_entries) == 1 else 'ies'} created."
        )
    elif mode == "append_dedup":
        st.success(
            f"{len(created_entries)} entr{'y' if len(created_entries) == 1 else 'ies'} created. "
            f"{len(skipped_duplicates)} duplicate question"
            f"{'' if len(skipped_duplicates) == 1 else 's'} skipped."
        )
    else:
        st.success(
            f"{len(created_entries)} QA dataset entr{'y' if len(created_entries) == 1 else 'ies'} created."
        )

    if skipped_duplicates:
        st.markdown("#### Skipped duplicate questions")
        for question in skipped_duplicates:
            st.markdown(f"- {question}")

    if created_entries:
        st.markdown("#### Created entries")
        for entry in created_entries:
            with st.expander(f"#{entry.id} — {entry.question}", expanded=False):
                if entry.expected_answer:
                    st.markdown("**Expected answer**")
                    st.write(entry.expected_answer)

                if entry.expected_doc_ids:
                    st.markdown("**Expected doc_ids**")
                    st.code("\n".join(entry.expected_doc_ids), language="text")

                if entry.expected_sources:
                    st.markdown("**Expected source files**")
                    st.code("\n".join(entry.expected_sources), language="text")


generate_clicked = st.button(
    "Generate QA dataset entries",
    use_container_width=True,
    disabled=is_request_running(DATASET_GENERATION_REQUEST_KEY),
)

if generate_clicked and not project_documents:
    st.warning("Please ingest documents before generating QA dataset entries.")
else:
    run_request_action(
        request_key=DATASET_GENERATION_REQUEST_KEY,
        result_key=DATASET_GENERATION_RESULT_KEY,
        trigger=generate_clicked,
        can_run=bool(project_documents),
        action=_run_dataset_generation,
        spinner_text="Generating QA dataset entries from project assets...",
        error_mapper=_map_dataset_generation_error,
    )

render_result_payload(
    result_key=DATASET_GENERATION_RESULT_KEY,
    on_success=_render_dataset_generation_result,
)

st.markdown("---")
st.markdown("### Add an entry manually")

with st.form("qa_dataset_create_form", clear_on_submit=True):
    dataset_question = st.text_area(
        "Dataset question",
        placeholder="e.g. What is the main objective of the report?",
        height=110,
    )

    dataset_expected_answer = st.text_area(
        "Expected answer (optional)",
        placeholder="Reference answer used later for evaluation and LLM-as-a-judge scoring.",
        height=120,
    )

    col1, col2 = st.columns(2)

    with col1:
        dataset_expected_doc_ids = st.text_input(
            "Expected doc_ids (optional, comma-separated)",
            placeholder="doc_1, doc_2",
        )

    with col2:
        dataset_expected_sources = st.text_input(
            "Expected source files (optional, comma-separated)",
            placeholder="report.pdf, appendix.pdf",
        )

    add_entry_clicked = st.form_submit_button(
        "Add QA entry",
        use_container_width=True,
    )

if add_entry_clicked:
    try:
        entry = app.create_qa_dataset_entry(
            user_id=user_id,
            project_id=project_id,
            question=dataset_question,
            expected_answer=dataset_expected_answer or None,
            expected_doc_ids=_parse_csv_list(dataset_expected_doc_ids),
            expected_sources=_parse_csv_list(dataset_expected_sources),
        )
        st.session_state["qa_dataset_success_message"] = (
            f"QA entry #{entry.id} added to project dataset."
        )
        st.rerun()
    except Exception as exc:
        st.session_state["qa_dataset_error_message"] = get_user_error_message(
            exc,
            f"Unable to add QA dataset entry: {exc}",
        )
        st.rerun()

entries = app.list_qa_dataset_entries(
    user_id=user_id,
    project_id=project_id,
)

m1, m2 = st.columns(2)
with m1:
    st.metric("Dataset entries", len(entries))
with m2:
    st.metric("Current project", project_id)

if not entries:
    st.info("No gold QA entries yet for this project.")
else:
    st.markdown("### Existing dataset entries")

    for entry in entries:
        with st.expander(f"#{entry.id} — {entry.question}", expanded=False):
            st.markdown("**Question**")
            st.write(entry.question)

            if entry.expected_answer:
                st.markdown("**Expected answer**")
                st.write(entry.expected_answer)
            else:
                st.caption("No expected answer provided.")

            doc_ids = entry.expected_doc_ids or []
            sources = entry.expected_sources or []

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Expected doc_ids**")
                if doc_ids:
                    st.code("\n".join(doc_ids), language="text")
                else:
                    st.caption("No expected doc_ids.")

            with c2:
                st.markdown("**Expected source files**")
                if sources:
                    st.code("\n".join(sources), language="text")
                else:
                    st.caption("No expected source files.")

            if entry.created_at:
                st.caption(f"Created: {entry.created_at}")
            if entry.updated_at:
                st.caption(f"Updated: {entry.updated_at}")

            if st.button(
                "Delete entry",
                key=f"delete_qa_entry_{entry.id}",
                use_container_width=True,
            ):
                try:
                    app.delete_qa_dataset_entry(
                        entry_id=entry.id,
                        user_id=user_id,
                        project_id=project_id,
                    )
                    st.session_state["qa_dataset_success_message"] = (
                        f"QA entry #{entry.id} deleted."
                    )
                except Exception as exc:
                    st.session_state["qa_dataset_error_message"] = get_user_error_message(
                        exc,
                        f"Unable to delete QA dataset entry #{entry.id}: {exc}",
                    )
                st.rerun()

st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<div class="card-title">Dataset retrieval metrics</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="card-subtitle">Run project-level retrieval evaluation over the gold QA dataset and inspect aggregated metrics.</div>',
    unsafe_allow_html=True,
)

dataset_eval_col1, dataset_eval_col2 = st.columns(2)

with dataset_eval_col1:
    dataset_enable_query_rewrite = st.toggle(
        "Enable query rewrite for dataset evaluation",
        value=True,
        help="Apply the same retrieval rewrite stage to every dataset question.",
    )

with dataset_eval_col2:
    dataset_enable_hybrid_retrieval = st.toggle(
        "Enable hybrid retrieval for dataset evaluation",
        value=True,
        help="Combine FAISS and BM25 during dataset evaluation.",
    )


def _run_dataset_evaluation():
    return app.evaluate_gold_qa_dataset(
        user_id=user_id,
        project_id=project_id,
        enable_query_rewrite=dataset_enable_query_rewrite,
        enable_hybrid_retrieval=dataset_enable_hybrid_retrieval,
    )


def _map_dataset_evaluation_error(exc: Exception) -> str:
    if isinstance(exc, VectorStoreError):
        return get_user_error_message(exc, "Unable to query the FAISS index for dataset evaluation.")
    if isinstance(exc, DocStoreError):
        return get_user_error_message(exc, "Unable to inspect supporting assets from SQLite during dataset evaluation.")
    if isinstance(exc, LLMServiceError):
        return get_user_error_message(exc, "The language model failed while preparing a retrieval pipeline during dataset evaluation.")
    return get_user_error_message(exc, f"Unexpected error while running dataset evaluation: {exc}")


def _render_dataset_evaluation_result(payload: dict):
    summary = payload["summary"]
    rows = payload["rows"]

    top_metrics = st.columns(5)
    with top_metrics[0]:
        st.metric("Entries", summary["total_entries"])
    with top_metrics[1]:
        st.metric("Successful queries", summary["successful_queries"])
    with top_metrics[2]:
        st.metric("Avg doc_id recall", summary["avg_doc_id_recall"])
    with top_metrics[3]:
        st.metric("Avg source recall", summary["avg_source_recall"])
    with top_metrics[4]:
        st.metric("Avg confidence", summary["avg_confidence"])

    bottom_metrics = st.columns(5)
    with bottom_metrics[0]:
        st.metric("Avg latency (ms)", summary["avg_latency_ms"])
    with bottom_metrics[1]:
        st.metric("Doc_id hit rate", summary["doc_id_hit_rate"])
    with bottom_metrics[2]:
        st.metric("Source hit rate", summary["source_hit_rate"])
    with bottom_metrics[3]:
        st.metric("Entries with expected doc_ids", summary["entries_with_expected_doc_ids"])
    with bottom_metrics[4]:
        st.metric("Entries with expected sources", summary["entries_with_expected_sources"])

    st.markdown("### Per-entry metrics")
    st.dataframe(rows, use_container_width=True)


dataset_run_clicked = st.button(
    "Run dataset evaluation",
    use_container_width=True,
    disabled=is_request_running(DATASET_EVALUATION_REQUEST_KEY),
)

if dataset_run_clicked and not entries:
    st.warning("Please add at least one gold QA dataset entry before running dataset evaluation.")
else:
    run_request_action(
        request_key=DATASET_EVALUATION_REQUEST_KEY,
        result_key=DATASET_EVALUATION_RESULT_KEY,
        trigger=dataset_run_clicked,
        can_run=bool(entries),
        action=_run_dataset_evaluation,
        spinner_text="Running dataset retrieval metrics...",
        error_mapper=_map_dataset_evaluation_error,
    )

render_result_payload(
    result_key=DATASET_EVALUATION_RESULT_KEY,
    on_success=_render_dataset_evaluation_result,
)

st.markdown("</div>", unsafe_allow_html=True)
