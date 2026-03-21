"""
Dataset evaluation tab: benchmark the gold QA dataset with Overview / Entries sub-tabs.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import Any, cast
import uuid

import streamlit as st

from src.app.ragcraft_app import RAGCraftApp
from src.core.error_utils import get_user_error_message
from src.core.exceptions import DocStoreError, LLMServiceError, VectorStoreError
from src.domain.benchmark_result import BenchmarkResult, coerce_benchmark_result
from src.services.benchmark_comparison_service import BenchmarkComparisonService
from src.domain.qa_dataset_entry import QADatasetEntry
from src.ui.evaluation_dashboard import render_evaluation_dashboard
from src.ui.evaluation_question_detail import render_benchmark_row_detail
from src.ui.evaluation_reports_tab import render_evaluation_reports_tab
from src.ui.metric_help import render_metric_with_help
from src.ui.request_runner import is_request_running, render_result_payload, run_request_action

BENCHMARK_RUN_HISTORY_BY_PROJECT_KEY = "benchmark_run_history_by_project"
_BENCHMARK_HISTORY_CAP = 20


def _benchmark_history_for_project(project_id: str) -> list[dict[str, Any]]:
    root = st.session_state.get(BENCHMARK_RUN_HISTORY_BY_PROJECT_KEY)
    if not isinstance(root, dict):
        return []
    hist = root.get(project_id)
    return hist if isinstance(hist, list) else []


def _append_benchmark_to_history(
    *,
    project_id: str,
    result: BenchmarkResult,
    generated_at: object,
    enable_query_rewrite: bool | None = None,
    enable_hybrid_retrieval: bool | None = None,
) -> None:
    root = st.session_state.setdefault(BENCHMARK_RUN_HISTORY_BY_PROJECT_KEY, {})
    if not isinstance(root, dict):
        root = {}
        st.session_state[BENCHMARK_RUN_HISTORY_BY_PROJECT_KEY] = root
    hist = root.setdefault(project_id, [])
    if not isinstance(hist, list):
        hist = []
        root[project_id] = hist
    rid = (result.run_id or "")[:12]
    if isinstance(generated_at, datetime):
        tlabel = generated_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    else:
        tlabel = str(generated_at)[:32] if generated_at else ""
    qr_on = enable_query_rewrite is True
    hy_on = enable_hybrid_retrieval is True
    settings_bits: list[str] = []
    if enable_query_rewrite is not None:
        settings_bits.append("query rewrite on" if qr_on else "query rewrite off")
    if enable_hybrid_retrieval is not None:
        settings_bits.append("hybrid on" if hy_on else "hybrid off")
    settings = " · ".join(settings_bits)
    if rid and settings:
        label = f"{tlabel} · {rid} · {settings}"
    elif rid:
        label = f"{tlabel} · {rid}"
    elif settings:
        label = f"{tlabel} · {settings}" if tlabel else settings
    else:
        label = tlabel or f"run {len(hist) + 1}"
    entry: dict[str, Any] = {
        "run_id": result.run_id or "",
        "label": label,
        "summary": dict(result.summary.data),
        "failures": dict(result.failures) if result.failures else None,
    }
    if enable_query_rewrite is not None:
        entry["enable_query_rewrite"] = bool(enable_query_rewrite)
    if enable_hybrid_retrieval is not None:
        entry["enable_hybrid_retrieval"] = bool(enable_hybrid_retrieval)
    hist.append(entry)
    while len(hist) > _BENCHMARK_HISTORY_CAP:
        hist.pop(0)


def _run_label(entry: dict[str, Any], index: int) -> str:
    lab = entry.get("label")
    rid = entry.get("run_id") or ""
    short = f"{rid[:8]}…" if len(rid) > 8 else rid
    base = lab if isinstance(lab, str) else f"Run {index + 1}"
    parts = [f"{base} ({short})" if short else base]
    qr = entry.get("enable_query_rewrite")
    hy = entry.get("enable_hybrid_retrieval")
    if isinstance(qr, bool) and isinstance(hy, bool):
        parts.append(f"QR {'on' if qr else 'off'} · Hyb {'on' if hy else 'off'}")
    return " — ".join(parts)


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
        st.caption(
            "Judge averages and hallucination rate use only rows where the LLM judge succeeded; "
            "judge-failed entries are excluded from those aggregates."
        )
        m1, m2, m3 = st.columns(3)
        with m1:
            _summary_metric_cell(summary, "avg_groundedness_score", "Avg groundedness")
        with m2:
            _summary_metric_cell(summary, "avg_recall_at_k", "Avg Recall@K")
        with m3:
            _summary_metric_cell(
                summary, "hallucination_rate", "Hallucination rate", as_percent=True
            )

        m4, m5, m6 = st.columns(3)
        with m4:
            _summary_metric_cell(summary, "avg_answer_relevance_score", "Avg answer relevance")
        with m5:
            _summary_metric_cell(summary, "avg_citation_doc_id_f1", "Avg citation doc ID F1")
        with m6:
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
    failures: dict[str, Any] | None = None,
    multimodal_metrics: dict[str, Any] | None = None,
    auto_debug: list[dict[str, str]] | None = None,
) -> None:
    st.markdown("---")
    st.markdown("##### Run dataset evaluation")
    st.caption(
        "Aggregated retrieval, gold answer F1, prompt vs answer citation doc ID overlap, and judge metrics over all gold QA entries."
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
        raw_result = app.evaluate_gold_qa_dataset(
            user_id=user_id,
            project_id=project_id,
            enable_query_rewrite=dataset_enable_query_rewrite,
            enable_hybrid_retrieval=dataset_enable_hybrid_retrieval,
        )
        if isinstance(raw_result, BenchmarkResult):
            result = replace(raw_result, run_id=uuid.uuid4().hex[:12])
        else:
            result = raw_result
        return {
            "result": result,
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
            done = coerce_benchmark_result(payload.get("result"))
            if done is not None:
                _append_benchmark_to_history(
                    project_id=project_id,
                    result=done,
                    generated_at=payload.get("generated_at"),
                    enable_query_rewrite=payload.get("enable_query_rewrite"),
                    enable_hybrid_retrieval=payload.get("enable_hybrid_retrieval"),
                )

    render_result_payload(
        result_key=dataset_evaluation_result_key,
        on_success=_on_dataset_eval_success,
    )

    st.markdown("---")
    st.markdown("##### Structured results")

    comparison_rows: list[dict[str, Any]] | None = None
    failure_comparison_rows: list[dict[str, Any]] | None = None
    hist = _benchmark_history_for_project(project_id)
    if len(hist) >= 2:
        rev = list(reversed(hist))
        cmp_svc = BenchmarkComparisonService()
        st.caption(
            "**A** is the baseline run; **B** is the candidate. Numeric deltas in the dashboard are **B − A** "
            "(positive usually means B is higher; latency and failure-type rates invert — see the comparison card)."
        )
        c1, c2 = st.columns(2)
        with c1:
            ia = st.selectbox(
                "Baseline run (A)",
                options=list(range(len(rev))),
                index=len(rev) - 1,
                format_func=lambda i: _run_label(rev[i], i),
                key=f"dataset_benchmark_cmp_a_{wk}",
            )
        with c2:
            ib = st.selectbox(
                "Comparison run (B)",
                options=list(range(len(rev))),
                index=0,
                format_func=lambda i: _run_label(rev[i], i),
                key=f"dataset_benchmark_cmp_b_{wk}",
            )
        if ia != ib:
            sa = rev[ia].get("summary")
            sb = rev[ib].get("summary")
            if isinstance(sa, dict) and isinstance(sb, dict):
                comparison_rows = cmp_svc.compare(sa, sb)
            fa = rev[ia].get("failures")
            fb = rev[ib].get("failures")
            failure_comparison_rows = cmp_svc.compare_failure_counts(
                fa if isinstance(fa, dict) else None,
                fb if isinstance(fb, dict) else None,
            )
        else:
            st.caption(
                "You picked the **same** run for A and B, so there is nothing to compare. "
                "Choose two different entries from history."
            )
    elif len(hist) == 1:
        st.caption(
            "History has one run so far. Evaluate again to keep a second snapshot — then you can pick **A** (baseline) "
            "and **B** (candidate) side by side."
        )

    if (
        not summary
        and not rows
        and comparison_rows is None
        and failure_comparison_rows is None
    ):
        st.info("Run **dataset evaluation** above to populate retrieval, judge, and per-entry metrics.")
    else:
        render_evaluation_dashboard(
            summary or {},
            rows or [],
            widget_key_prefix=f"dataset_eval_metrics_{wk}",
            correlations=correlations,
            failures=failures,
            multimodal_metrics=multimodal_metrics,
            auto_debug=auto_debug,
            comparison=comparison_rows,
            failure_comparison=failure_comparison_rows,
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
    failures = cast(dict[str, Any] | None, payload.get("failures"))
    multimodal_metrics = cast(dict[str, Any] | None, payload.get("multimodal_metrics"))
    auto_debug = cast(list[dict[str, str]] | None, payload.get("auto_debug"))

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
            failures=failures,
            multimodal_metrics=multimodal_metrics,
            auto_debug=auto_debug,
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
