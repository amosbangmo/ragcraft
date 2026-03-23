"""
Evaluation hub. Dataset benchmark and related calls use :class:`~services.api_client.BackendClient`
(``POST /evaluation/dataset/run`` and siblings when ``RAGCRAFT_BACKEND_CLIENT=http``).
"""

from typing import Any

import streamlit as st

from components.shared.evaluation_tabs import render_evaluation_tabs
from components.shared.layout import apply_layout
from components.shared.page_header import render_page_header
from components.shared.request_runner import analyze_dataset_evaluation_session_payload
from infrastructure.auth.guards import require_authentication
from services.api_client import BackendClient, BenchmarkResult

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

_EVAL_PAGE_LAST_PROJECT_KEY = "_eval_page_last_project_id"
BENCHMARK_RUN_HISTORY_BY_PROJECT_KEY = "benchmark_run_history_by_project"


def _evaluation_widget_key_suffix(project_id: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in project_id)[:80]


def _reset_evaluation_context_if_project_changed(project_id: str) -> str:
    """
    When "Project for evaluation" changes, drop cached runs and dashboard widget state
    so each tab reflects the newly selected project.
    """
    suffix = _evaluation_widget_key_suffix(project_id)
    last = st.session_state.get(_EVAL_PAGE_LAST_PROJECT_KEY)
    if last is not None and last != project_id:
        for k in (
            EVALUATION_REQUEST_KEY,
            EVALUATION_RESULT_KEY,
            DATASET_GENERATION_REQUEST_KEY,
            DATASET_GENERATION_RESULT_KEY,
            DATASET_EVALUATION_REQUEST_KEY,
            DATASET_EVALUATION_RESULT_KEY,
            "_eval_invalid_dataset_payload_warned_for",
        ):
            st.session_state.pop(k, None)
        st.session_state.pop("qa_dataset_success_message", None)
        st.session_state.pop("qa_dataset_error_message", None)
        st.session_state.pop(BENCHMARK_RUN_HISTORY_BY_PROJECT_KEY, None)
        for k in list(st.session_state.keys()):
            if k.startswith(("dataset_eval_metrics_", "delete_qa_entry_dataset_")):
                st.session_state.pop(k, None)
    st.session_state[_EVAL_PAGE_LAST_PROJECT_KEY] = project_id
    return suffix


def _session_benchmark_bundle() -> tuple[dict[str, Any], BenchmarkResult] | None:
    raw = st.session_state.get(DATASET_EVALUATION_RESULT_KEY)
    view = analyze_dataset_evaluation_session_payload(raw)
    if view.kind == "ok" and view.result is not None and isinstance(raw, dict):
        st.session_state.pop("_eval_invalid_dataset_payload_warned_for", None)
        return raw, view.result
    if view.kind == "invalid_result":
        wkey = "_eval_invalid_dataset_payload_warned_for"
        rid = id(raw)
        if st.session_state.get(wkey) != rid:
            st.warning(
                "A dataset evaluation payload is in this session but could not be loaded. "
                "Run **dataset evaluation** again to refresh metrics and exports."
            )
            st.session_state[wkey] = rid
    return None


header = render_page_header(
    badge="Evaluation",
    title="Test answer quality",
    subtitle="Run manual evaluation queries, manage a gold QA dataset, and compute retrieval metrics for the current project.",
    selector_label="Project for evaluation",
)

client: BackendClient = header["backend_client"]
user_id = str(header["user_id"])
project_id = str(header["project_id"]) if header["project_id"] else None

if not project_id:
    st.stop()

eval_widget_suffix = _reset_evaluation_context_if_project_changed(project_id)

project_documents = client.list_project_documents(user_id, project_id)

if "qa_dataset_success_message" in st.session_state:
    st.success(st.session_state.pop("qa_dataset_success_message"))

if "qa_dataset_error_message" in st.session_state:
    st.error(st.session_state.pop("qa_dataset_error_message"))

entries = client.list_qa_dataset_entries(
    user_id=user_id,
    project_id=project_id,
)

bundle = _session_benchmark_bundle()
summary: dict[str, Any] = {}
rows: list[dict[str, Any]] = []
correlations: dict[str, Any] | None = None
failures: dict[str, Any] | None = None
multimodal_metrics: dict[str, Any] | None = None
auto_debug: list[dict[str, str]] | None = None
bench_for_tabs: BenchmarkResult | None = None

if bundle is not None:
    _, bench_for_tabs = bundle
    summary = bench_for_tabs.summary.to_dict()
    rows = [row.to_dict() for row in bench_for_tabs.rows]
    correlations = bench_for_tabs.correlations
    failures = bench_for_tabs.failures
    multimodal_metrics = bench_for_tabs.multimodal_metrics
    auto_debug = bench_for_tabs.auto_debug

render_evaluation_tabs(
    manual_payload={
        "backend_client": client,
        "user_id": user_id,
        "project_id": project_id,
        "widget_key_suffix": eval_widget_suffix,
        "evaluation_request_key": EVALUATION_REQUEST_KEY,
        "evaluation_result_key": EVALUATION_RESULT_KEY,
    },
    dataset_payload={
        "backend_client": client,
        "user_id": user_id,
        "project_id": project_id,
        "widget_key_suffix": eval_widget_suffix,
        "entries": entries,
        "dataset_evaluation_request_key": DATASET_EVALUATION_REQUEST_KEY,
        "dataset_evaluation_result_key": DATASET_EVALUATION_RESULT_KEY,
        "summary": summary,
        "rows": rows,
        "correlations": correlations,
        "failures": failures,
        "multimodal_metrics": multimodal_metrics,
        "auto_debug": auto_debug,
    },
    gold_qa_payload={
        "backend_client": client,
        "user_id": user_id,
        "project_id": project_id,
        "widget_key_suffix": eval_widget_suffix,
        "project_documents": project_documents,
        "dataset_generation_request_key": DATASET_GENERATION_REQUEST_KEY,
        "dataset_generation_result_key": DATASET_GENERATION_RESULT_KEY,
        "entry_count": len(entries),
    },
    retrieval_payload={
        "user_id": user_id,
        "backend_client": client,
        "project_id": project_id,
        "widget_key_suffix": eval_widget_suffix,
    },
)
