import streamlit as st

from typing import Any, cast

from src.app.ragcraft_app import RAGCraftApp
from src.domain.benchmark_result import BenchmarkResult, coerce_benchmark_result
from src.domain.manual_evaluation_result import ManualEvaluationResult, is_manual_evaluation_result_like
from src.ui.layout import apply_layout
from src.ui.page_header import render_page_header
from src.ui.evaluation_tabs import render_evaluation_tabs
from src.auth.guards import require_authentication


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
        ):
            st.session_state.pop(k, None)
        st.session_state.pop("qa_dataset_success_message", None)
        st.session_state.pop("qa_dataset_error_message", None)
        for k in list(st.session_state.keys()):
            if k.startswith(
                ("dataset_eval_metrics_", "analysis_eval_dashboard_", "delete_qa_entry_dataset_")
            ):
                st.session_state.pop(k, None)
    st.session_state[_EVAL_PAGE_LAST_PROJECT_KEY] = project_id
    return suffix


def _session_benchmark_bundle() -> tuple[dict[str, Any], BenchmarkResult] | None:
    raw = st.session_state.get(DATASET_EVALUATION_RESULT_KEY)
    if raw is None or not isinstance(raw, dict) or "error" in raw:
        return None
    result = raw.get("result")
    coerced = coerce_benchmark_result(result)
    if coerced is None:
        return None
    return raw, coerced


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

eval_widget_suffix = _reset_evaluation_context_if_project_changed(project_id)

project_documents = app.list_project_documents(user_id, project_id)

if "qa_dataset_success_message" in st.session_state:
    st.success(st.session_state.pop("qa_dataset_success_message"))

if "qa_dataset_error_message" in st.session_state:
    st.error(st.session_state.pop("qa_dataset_error_message"))

entries = app.list_qa_dataset_entries(
    user_id=user_id,
    project_id=project_id,
)

manual_for_tabs: ManualEvaluationResult | None = None
manual_payload_raw = st.session_state.get(EVALUATION_RESULT_KEY)
if is_manual_evaluation_result_like(manual_payload_raw):
    manual_for_tabs = cast(ManualEvaluationResult, manual_payload_raw)

bundle = _session_benchmark_bundle()
summary: dict[str, Any] = {}
rows: list[dict[str, Any]] = []
bench_for_tabs: BenchmarkResult | None = None
reports_export = None

if bundle is not None:
    payload_dict, bench_for_tabs = bundle
    summary = bench_for_tabs.summary.to_dict()
    rows = [row.to_dict() for row in bench_for_tabs.rows]
    reports_export = app.build_benchmark_export_artifacts(
        project_id=project_id,
        result=bench_for_tabs,
        enable_query_rewrite=bool(payload_dict.get("enable_query_rewrite")),
        enable_hybrid_retrieval=bool(payload_dict.get("enable_hybrid_retrieval")),
        generated_at=payload_dict.get("generated_at"),
    )

render_evaluation_tabs(
    manual_payload={
        "app": app,
        "user_id": user_id,
        "project_id": project_id,
        "widget_key_suffix": eval_widget_suffix,
        "evaluation_request_key": EVALUATION_REQUEST_KEY,
        "evaluation_result_key": EVALUATION_RESULT_KEY,
    },
    dataset_payload={
        "app": app,
        "user_id": user_id,
        "project_id": project_id,
        "widget_key_suffix": eval_widget_suffix,
        "entries": entries,
        "dataset_evaluation_request_key": DATASET_EVALUATION_REQUEST_KEY,
        "dataset_evaluation_result_key": DATASET_EVALUATION_RESULT_KEY,
        "summary": summary,
        "rows": rows,
    },
    gold_qa_payload={
        "app": app,
        "user_id": user_id,
        "project_id": project_id,
        "widget_key_suffix": eval_widget_suffix,
        "project_documents": project_documents,
        "dataset_generation_request_key": DATASET_GENERATION_REQUEST_KEY,
        "dataset_generation_result_key": DATASET_GENERATION_RESULT_KEY,
        "entry_count": len(entries),
    },
    analysis_payload={
        "reports_export": reports_export,
        "manual_result": manual_for_tabs,
        "summary": summary,
        "rows": rows,
        "widget_key_suffix": eval_widget_suffix,
    },
)
