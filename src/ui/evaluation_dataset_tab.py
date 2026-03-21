"""
Dataset evaluation tab: benchmark the gold QA dataset with Overview / Entries sub-tabs.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, cast

import streamlit as st

from src.app.ragcraft_app import RAGCraftApp
from src.core.error_utils import get_user_error_message
from src.core.exceptions import DocStoreError, LLMServiceError, VectorStoreError
from src.domain.benchmark_result import BenchmarkResult, coerce_benchmark_result
from src.domain.qa_dataset_entry import QADatasetEntry
from src.ui.evaluation_dashboard import render_evaluation_dashboard
from src.ui.evaluation_question_detail import render_benchmark_row_detail
from src.ui.evaluation_reports_tab import render_evaluation_reports_tab
from src.ui.metric_help import render_metric_with_help
from src.ui.request_runner import is_request_running, render_result_payload, run_request_action


def _coerce_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _summary_metric_cell(summary: dict, key: str, label: str, *, as_percent: bool = False) -> None:
    raw = summary.get(key)
    num = _coerce_float(raw)
    if num is None:
        render_metric_with_help(label=label, value="—", metric_key=key)
        return
    if as_percent:
        render_metric_with_help(
            label=label, value=f"{num * 100:.1f}%", metric_key=key
        )
    else:
        render_metric_with_help(label=label, value=num, metric_key=key)


def _render_dataset_overview(
    *,
    project_id: str,
    entry_count: int,
    summary: dict[str, Any],
    rows: list[dict[str, Any]],
) -> None:
    st.markdown("##### At a glance")
    c1, c2 = st.columns(2)
    with c1:
        render_metric_with_help(
            label="Dataset entries",
            value=entry_count,
            metric_key="dataset_entry_count",
        )
    with c2:
        render_metric_with_help(
            label="Current project",
            value=project_id,
            metric_key="evaluation_project_context"
        )

    if not summary and not rows:
        st.info(
            "Add gold QA entries under **Gold QA dataset**, then run **dataset evaluation** below."
        )
    else:
        st.markdown("##### Latest benchmark (summary)")
        m1, m2, m3 = st.columns(3)
        with m1:
            _summary_metric_cell(summary, "avg_groundedness", "Avg groundedness")
        with m2:
            _summary_metric_cell(summary, "avg_doc_id_recall", "Avg doc ID recall")
        with m3:
            _summary_metric_cell(
                summary, "hallucination_rate", "Hallucination rate", as_percent=True
            )

        m4, m5 = st.columns(2)
        with m4:
            _summary_metric_cell(summary, "avg_answer_relevance", "Avg answer relevance")
        with m5:
            _summary_metric_cell(summary, "avg_confidence", "Avg confidence")


def _render_dataset_evaluation_run_and_results(
    *,
    app: RAGCraftApp,
    user_id: str,
    project_id: str,
    wk: str,
    entries: list[QADatasetEntry],
    dataset_evaluation_request_key: str,
    dataset_evaluation_result_key: str,
    summary: dict[str, Any],
    rows: list[dict[str, Any]],
    correlations: dict[str, Any] | None = None,
) -> None:
    st.markdown("---")
    st.markdown("##### Run dataset evaluation")
    st.caption(
        "Aggregated retrieval, answer, citation, and judge metrics over all gold QA entries."
    )

    dataset_eval_col1, dataset_eval_col2 = st.columns(2)
    with dataset_eval_col1:
        dataset_enable_query_rewrite = st.toggle(
            "Enable query rewrite for dataset evaluation",
            value=True,
            help="Apply the same retrieval rewrite stage to every dataset question.",
            key=f"eval_ds_query_rewrite_{wk}",
        )
    with dataset_eval_col2:
        dataset_enable_hybrid_retrieval = st.toggle(
            "Enable hybrid retrieval for dataset evaluation",
            value=True,
            help="Combine FAISS and BM25 during dataset evaluation.",
            key=f"eval_ds_hybrid_{wk}",
        )

    def _run_dataset_evaluation():
        return {
            "result": app.evaluate_gold_qa_dataset(
                user_id=user_id,
                project_id=project_id,
                enable_query_rewrite=dataset_enable_query_rewrite,
                enable_hybrid_retrieval=dataset_enable_hybrid_retrieval,
            ),
            "enable_query_rewrite": dataset_enable_query_rewrite,
            "enable_hybrid_retrieval": dataset_enable_hybrid_retrieval,
            "generated_at": datetime.now(timezone.utc),
        }

    def _map_dataset_evaluation_error(exc: Exception) -> str:
        if isinstance(exc, VectorStoreError):
            return get_user_error_message(exc, "Unable to query the FAISS index for dataset evaluation.")
        if isinstance(exc, DocStoreError):
            return get_user_error_message(
                exc,
                "Unable to inspect supporting assets from SQLite during dataset evaluation.",
            )
        if isinstance(exc, LLMServiceError):
            return get_user_error_message(
                exc,
                "The language model failed while preparing a retrieval pipeline during dataset evaluation.",
            )
        return get_user_error_message(exc, f"Unexpected error while running dataset evaluation: {exc}")

    dataset_run_clicked = st.button(
        "Run dataset evaluation",
        use_container_width=True,
        disabled=is_request_running(dataset_evaluation_request_key),
        key=f"eval_ds_run_benchmark_{wk}",
    )

    if dataset_run_clicked and not entries:
        st.warning("Please add at least one gold QA dataset entry before running dataset evaluation.")
    else:
        run_request_action(
            request_key=dataset_evaluation_request_key,
            result_key=dataset_evaluation_result_key,
            trigger=dataset_run_clicked,
            can_run=bool(entries),
            action=_run_dataset_evaluation,
            spinner_text="Running dataset retrieval metrics...",
            error_mapper=_map_dataset_evaluation_error,
        )

    def _on_dataset_eval_success(payload: Any) -> None:
        if isinstance(payload, dict) and "result" in payload and "error" not in payload:
            st.success("Dataset evaluation completed. Structured results appear below.")

    render_result_payload(
        result_key=dataset_evaluation_result_key,
        on_success=_on_dataset_eval_success,
    )

    st.markdown("---")
    st.markdown("##### Structured results")
    if not summary and not rows:
        st.info("Run **dataset evaluation** above to populate retrieval, judge, and per-entry metrics.")
    else:
        render_evaluation_dashboard(
            summary,
            rows,
            widget_key_prefix=f"dataset_eval_metrics_{wk}",
            correlations=correlations,
        )


def _resolve_benchmark_export_artifacts(
    *,
    app: RAGCraftApp,
    project_id: str,
    dataset_evaluation_result_key: str,
    summary: dict[str, Any],
    rows: list[dict[str, Any]],
) -> Any:
    """
    Build download artifacts from the same session payload as the benchmark run.

    Resolving here (not only on the page module) keeps exports aligned with
    ``st.session_state`` after a run and avoids stale or missing precomputed exports.
    """
    raw = st.session_state.get(dataset_evaluation_result_key)
    if raw is None or not isinstance(raw, dict) or "error" in raw:
        return None

    result = coerce_benchmark_result(raw.get("result"))
    if result is None:
        if not summary and not rows:
            return None
        try:
            result = BenchmarkResult.from_plain_dict({"summary": summary, "rows": rows})
        except (TypeError, ValueError, KeyError):
            return None

    return app.build_benchmark_export_artifacts(
        project_id=project_id,
        result=result,
        enable_query_rewrite=bool(raw.get("enable_query_rewrite")),
        enable_hybrid_retrieval=bool(raw.get("enable_hybrid_retrieval")),
        generated_at=raw.get("generated_at"),
    )


def _render_reports_exports_and_benchmark_json(
    *,
    app: RAGCraftApp,
    project_id: str,
    dataset_evaluation_result_key: str,
    summary: dict[str, Any],
    rows: list[dict[str, Any]],
) -> None:
    st.markdown("---")
    export = _resolve_benchmark_export_artifacts(
        app=app,
        project_id=project_id,
        dataset_evaluation_result_key=dataset_evaluation_result_key,
        summary=summary,
        rows=rows,
    )
    render_evaluation_reports_tab({"export": export})
    if summary or rows:
        with st.expander("Benchmark summary JSON", expanded=False):
            st.json(summary)


def _rows_by_entry_id(rows: list[dict[str, Any]]) -> dict[Any, dict[str, Any]]:
    out: dict[Any, dict[str, Any]] = {}
    for row in rows:
        eid = row.get("entry_id")
        if eid is not None:
            out[eid] = row
    return out


def render_evaluation_dataset_tab(payload: dict[str, Any]) -> None:
    app = cast(RAGCraftApp, payload["app"])
    user_id = str(payload["user_id"])
    project_id = str(payload["project_id"])
    wk = str(payload["widget_key_suffix"])
    entries = cast(list[QADatasetEntry], payload["entries"])
    dataset_evaluation_request_key = str(payload["dataset_evaluation_request_key"])
    dataset_evaluation_result_key = str(payload["dataset_evaluation_result_key"])
    summary = cast(dict[str, Any], payload.get("summary") or {})
    rows = cast(list[dict[str, Any]], payload.get("rows") or [])
    correlations = cast(dict[str, Any] | None, payload.get("correlations"))

    st.caption(
        "Benchmark the gold QA dataset for this project: run evaluation and review aggregates on **Overview**, "
        "or inspect and manage entries on **Entries**."
    )

    tab_overview, tab_entries = st.tabs(["Overview", "Entries"])

    with tab_overview:
        _render_dataset_overview(
            project_id=project_id,
            entry_count=len(entries),
            summary=summary,
            rows=rows,
        )
        _render_dataset_evaluation_run_and_results(
            app=app,
            user_id=user_id,
            project_id=project_id,
            wk=wk,
            entries=entries,
            dataset_evaluation_request_key=dataset_evaluation_request_key,
            dataset_evaluation_result_key=dataset_evaluation_result_key,
            summary=summary,
            rows=rows,
            correlations=correlations,
        )
        _render_reports_exports_and_benchmark_json(
            app=app,
            project_id=project_id,
            dataset_evaluation_result_key=dataset_evaluation_result_key,
            summary=summary,
            rows=rows,
        )

    with tab_entries:
        st.markdown("##### Entries")
        st.caption("Every gold QA row used for dataset evaluation. Open a row for details.")
        if not entries:
            st.info("No gold QA entries yet. Add them under **Gold QA dataset**.")
        else:
            bench_rows = _rows_by_entry_id(rows)
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

                    br = bench_rows.get(entry.id)
                    if isinstance(br, dict):
                        with st.expander("Latest benchmark scores for this entry", expanded=False):
                            render_benchmark_row_detail(br, include_full_row_json_expander=True)
                    else:
                        st.caption("Run dataset evaluation from the **Overview** tab to attach scores to this entry.")

                    if st.button(
                        "Delete entry",
                        key=f"delete_qa_entry_dataset_{wk}_{entry.id}",
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
