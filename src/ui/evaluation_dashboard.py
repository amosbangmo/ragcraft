"""
Unified benchmark dashboard: retrieval, overlap, LLM-judge, pipeline, multimodal, and failure views.

Cards in ``render_evaluation_dashboard`` follow the families in
:mod:`src.domain.benchmark_metric_taxonomy` (ranked-doc retrieval, sources, pipeline runtime,
gold-answer overlap, prompt/citation doc-ID overlap, judge scores, then multimodal when present).
"""

from __future__ import annotations

from typing import Any

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from src.frontend_gateway.view_models import LOWER_IS_BETTER_METRICS, FailureAnalysisService
from src.ui.evaluation_summary_metrics import (
    coerce_float_for_summary_metric as _coerce_float,
    render_summary_metric_from_mapping as _summary_metric,
)
from src.ui.metric_help import render_metric_with_help
from src.ui.section_card import inject_section_card_styles, section_card


def _coerce_hallucination_flag(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes"}
    if isinstance(value, (int, float)):
        return bool(value)
    return False


def _row_hallucination_flag(row: dict) -> bool:
    if row.get("judge_failed"):
        return False
    return _coerce_hallucination_flag(row.get("has_hallucination"))


def _dataframe_judge_valid_for_hallucination(df: pd.DataFrame) -> pd.DataFrame:
    """Rows used for hallucination flag counts in the dashboard (excludes judge failures)."""
    if "judge_failed" not in df.columns:
        return df
    return df[df["judge_failed"].ne(True)].reset_index(drop=True)


def _row_answer_text(row: dict) -> str | None:
    for key in ("answer", "answer_preview", "generated_answer"):
        val = row.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


# Cap fractional tick labels at 2 decimal places on float axes (d3-format).
_FLOAT_AXIS_2DP = alt.Axis(format=".2f")
_INT_AXIS = alt.Axis(format="d")


def _render_correlation_analysis(
    correlations: dict[str, Any] | None,
    rows: list[dict],
) -> None:
    with st.expander("Correlation analysis", expanded=False):
        st.caption(
            "Pearson correlation (r) across rows. **answer_f1** is token F1 vs the gold answer. "
            "Prompt metrics use doc IDs from prompt sources; citation metrics use **[Source N]** "
            "labels parsed from the reply. |r| ≥ 0.6 is treated as a strong linear association."
        )
        if not correlations:
            st.caption("Correlations are attached after each dataset evaluation run.")
            return
        if not correlations.get("available"):
            reason = correlations.get("reason")
            extra = f" ({reason})" if reason else ""
            st.caption(f"Not enough overlapping numeric metrics or rows.{extra}")
            return

        thr = float(correlations.get("strong_threshold") or 0.6)
        metrics = list(correlations.get("metrics_used") or [])
        matrix = correlations.get("matrix") or {}
        records: list[dict] = []
        for i, a in enumerate(metrics):
            for b in metrics[i + 1 :]:
                row_m = matrix.get(a) if isinstance(matrix.get(a), dict) else None
                r = row_m.get(b) if row_m else None
                if r is None:
                    continue
                records.append(
                    {
                        "metric_a": a,
                        "metric_b": b,
                        "r": round(float(r), 4),
                        "strong": abs(float(r)) >= thr,
                    }
                )
        records.sort(key=lambda x: abs(x["r"]), reverse=True)

        sp = correlations.get("highlights", {}).get("strong_positive") or []
        sn = correlations.get("highlights", {}).get("strong_negative") or []
        if sp:
            st.markdown("**Strong positive (r ≥ {:.1f})**".format(thr))
            for item in sp[:6]:
                st.caption(
                    f"• {item['metric_a']} ↔ {item['metric_b']}: **{item['r']}**"
                )
        if sn:
            st.markdown("**Strong negative (r ≤ -{:.1f})**".format(thr))
            for item in sn[:6]:
                st.caption(
                    f"• {item['metric_a']} ↔ {item['metric_b']}: **{item['r']}**"
                )
        if not sp and not sn:
            st.caption("No pairs reached the strong |r| threshold for this run.")

        if records:
            st.markdown("**All pairwise correlations** (|r| descending)")
            st.dataframe(
                pd.DataFrame(records),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("No finite pairwise correlations (e.g. constant columns or too few points).")

        n = int(correlations.get("sample_size") or 0)
        st.caption(f"Based on **{n}** evaluated row(s).")

        with st.expander("Optional: scatter — confidence vs answer F1", expanded=False):
            if not rows:
                st.caption("No rows to plot.")
            else:
                df = pd.DataFrame(rows)
                c = _numeric_series(df, "confidence")
                f1 = _numeric_series(df, "answer_f1")
                if c is not None and f1 is not None:
                    sc = pd.DataFrame({"confidence": c, "answer_f1": f1}).dropna()
                    if len(sc) >= 2:
                        chart = (
                            alt.Chart(sc)
                            .mark_circle()
                            .encode(
                                x=alt.X("confidence:Q", axis=_FLOAT_AXIS_2DP),
                                y=alt.Y("answer_f1:Q", title="answer F1", axis=_FLOAT_AXIS_2DP),
                            )
                        )
                        st.altair_chart(chart, use_container_width=True)
                    else:
                        st.caption("Need at least two rows with both confidence and answer F1.")
                else:
                    st.caption("Missing confidence or answer_f1 on rows.")


_FAILURE_TYPE_LABELS: dict[str, str] = {
    "retrieval_failure": "Retrieval miss",
    "context_selection_failure": "Context selection (prompt doc IDs)",
    "citation_failure": "Citation (answer doc IDs)",
    "judge_failure": "LLM judge failure",
    "grounding_failure": "Grounding / gold mismatch",
    "hallucination": "Hallucination signal",
    "low_relevance": "Low relevance",
    "low_confidence": "Low confidence",
    "table_misuse": "Table context + low gold F1",
    "image_hallucination": "Image context + hallucination signal",
}


def _resolve_failure_payload(
    failures: dict[str, Any] | None,
    rows: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if isinstance(failures, dict) and failures:
        return failures
    if not rows:
        return None

    analysis = FailureAnalysisService().analyze(list(rows))
    analysis.pop("row_failures", None)
    return analysis


def _render_failure_analysis(
    failures: dict[str, Any] | None,
    rows: list[dict[str, Any]],
) -> None:
    with st.expander("Failure analysis", expanded=False):
        st.caption(
            "Heuristic tags from retrieval, judge scores, prompt vs answer citation doc ID overlap, and gold answer F1. "
            "A row may match several types. Metrics missing on a row skip that rule. "
            "If this session predates failure analysis, counts are recomputed from the table below."
        )
        if not rows:
            st.caption("No rows to analyze.")
            return
        payload = _resolve_failure_payload(failures, rows)
        if not payload:
            st.caption("No failure summary available.")
            return

        counts_raw = payload.get("counts")
        counts: dict[str, Any] = counts_raw if isinstance(counts_raw, dict) else {}
        failed_n = int(payload.get("failed_row_count") or 0)
        crit_n = int(payload.get("critical_count") or 0)

        if crit_n > 0:
            st.error(
                f"**{crit_n}** critical row(s): high confidence with low gold answer F1 — review these first."
            )

        st.metric("Rows with ≥1 failure tag", failed_n)
        if not counts:
            st.success("No failure tags matched for this run.")
            return

        top_types = payload.get("top_failure_types") or []
        if isinstance(top_types, list) and top_types:
            st.markdown("**Top failure types**")
            lines: list[str] = []
            for item in top_types[:5]:
                if not isinstance(item, dict):
                    continue
                t = item.get("type")
                c = item.get("count")
                if t is None or c is None:
                    continue
                label = _FAILURE_TYPE_LABELS.get(str(t), str(t))
                lines.append(f"• **{label}**: {c}")
            if lines:
                st.markdown("\n".join(lines))

        chart_records: list[dict[str, Any]] = []
        for k, v in counts.items():
            if not isinstance(k, str):
                continue
            try:
                n = int(v)
            except (TypeError, ValueError):
                continue
            if n <= 0:
                continue
            chart_records.append(
                {
                    "failure_type": _FAILURE_TYPE_LABELS.get(k, k),
                    "count": n,
                }
            )
        chart_records.sort(key=lambda r: (-int(r["count"]), str(r["failure_type"])))
        if chart_records:
            st.markdown("**Distribution**")
            cdf = pd.DataFrame(chart_records)
            chart = (
                alt.Chart(cdf)
                .mark_bar()
                .encode(
                    x=alt.X("count:Q", title="Count", axis=_INT_AXIS),
                    y=alt.Y("failure_type:N", title="", sort="-x"),
                )
            )
            st.altair_chart(chart, use_container_width=True)

        examples = payload.get("examples") or {}
        if isinstance(examples, dict) and examples:
            st.markdown("**Sample failed queries** (up to 3 shown per type; 5 stored)")
            for ftype, xs in examples.items():
                if not isinstance(ftype, str) or not isinstance(xs, list) or not xs:
                    continue
                label = _FAILURE_TYPE_LABELS.get(ftype, ftype)
                show = xs[:3]
                for i, ex in enumerate(show):
                    if not isinstance(ex, dict):
                        continue
                    crit = bool(ex.get("failure_critical"))
                    eid = ex.get("entry_id", i)
                    title = f"#{eid} — {label}"
                    if crit:
                        title = f"CRITICAL — {title}"
                    with st.expander(title, expanded=False):
                        if crit:
                            st.caption("High confidence + low gold F1.")
                        flabels = ex.get("failure_labels")
                        if isinstance(flabels, list) and "judge_failure" in flabels:
                            st.caption(
                                "**Judge failure:** the LLM judge did not return usable scores for this row. "
                                "Empty judge metrics below are not zeros or hallucinations — treat this as an operational "
                                "scoring issue, not answer quality."
                            )
                        q = ex.get("question") or "—"
                        st.markdown("**Question**")
                        st.write(q)
                        prev = ex.get("answer_preview")
                        if isinstance(prev, str) and prev.strip():
                            st.markdown("**Answer preview**")
                            st.write(prev)
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            st.caption("Recall@K / answer F1")
                            st.write(f"{ex.get('recall_at_k', '—')} / {ex.get('answer_f1', '—')}")
                        with c2:
                            st.caption("Groundedness / hallucination score")
                            st.write(
                                f"{ex.get('groundedness_score', '—')} / "
                                f"{ex.get('hallucination_score', '—')}"
                            )
                        with c3:
                            st.caption("Relevance / confidence")
                            st.write(
                                f"{ex.get('answer_relevance_score', '—')} / "
                                f"{ex.get('confidence', '—')}"
                            )


def _numeric_series(df: pd.DataFrame, *candidates: str) -> pd.Series | None:
    for col in candidates:
        if col not in df.columns:
            continue
        s = pd.to_numeric(df[col], errors="coerce")
        if s.notna().any():
            return s
    return None


def _histogram_bar_chart(label: str, series: pd.Series | None) -> None:
    st.caption(label)
    if series is None:
        st.caption("No column data for this metric.")
        return
    s = series.dropna()
    if s.empty:
        st.caption("No numeric values to plot.")
        return
    n_bins = int(min(12, max(5, round(len(s) ** 0.5))))
    counts, edges = np.histogram(s.astype(float), bins=n_bins)
    mids = (edges[:-1] + edges[1:]) / 2.0
    chart_df = pd.DataFrame({"bin_mid": mids, "count": counts.astype(int)})
    chart = (
        alt.Chart(chart_df)
        .mark_bar()
        .encode(
            x=alt.X("bin_mid:Q", title="Value", axis=_FLOAT_AXIS_2DP),
            y=alt.Y("count:Q", title="Count", axis=_INT_AXIS),
        )
    )
    st.altair_chart(chart, use_container_width=True)


def render_overview_insight_charts(rows: list[dict]) -> None:
    """
    Lightweight charts for the Evaluation page Overview tab.
    Reuses the same histogram helper as the full dashboard.
    """
    if not rows:
        st.caption("Run dataset evaluation to see score distributions.")
        return
    df = pd.DataFrame(rows)
    if df.empty:
        st.caption("No rows available for charts.")
        return
    st.markdown("##### Score spread (this run)")
    c1, c2 = st.columns(2)
    with c1:
        _histogram_bar_chart(
            "Groundedness",
            _numeric_series(df, "groundedness_score"),
        )
    with c2:
        _histogram_bar_chart(
            "Recall@K",
            _numeric_series(df, "recall_at_k"),
        )


def _render_multimodal_performance(multimodal_metrics: dict[str, Any]) -> None:
    if not multimodal_metrics:
        return

    with section_card(
        title="Multimodal performance",
        subtitle="Usage of tables and images in retrieved context or prompt sources, mixed-modality prompts, and quality "
        "when those modalities appear.",
        min_height=0,
    ):
        u1, u2, u3 = st.columns(3)
        with u1:
            _summary_metric(
                multimodal_metrics,
                "table_usage_rate",
                "Table usage (retrieval or prompt sources)",
                as_percent=True,
            )
        with u2:
            _summary_metric(
                multimodal_metrics,
                "image_usage_rate",
                "Image usage (retrieval or prompt sources)",
                as_percent=True,
            )
        with u3:
            _summary_metric(
                multimodal_metrics,
                "multimodal_answers_rate",
                "Mixed-modality prompts (≥2 asset types)",
                as_percent=True,
            )

        q1, q2 = st.columns(2)
        with q1:
            _summary_metric(
                multimodal_metrics,
                "table_correctness",
                "Table rows — avg answer F1",
            )
        with q2:
            _summary_metric(
                multimodal_metrics,
                "image_groundedness",
                "Image rows — avg groundedness",
            )

        eligible = multimodal_metrics.get("eligible_rows")
        if eligible is not None:
            st.caption(f"Based on **{int(eligible)}** successful pipeline row(s) with modality metadata.")

        by_mod = multimodal_metrics.get("by_modality")
        if isinstance(by_mod, dict) and by_mod:
            st.markdown("##### Performance by modality context")
            records: list[dict[str, Any]] = []
            labels = {
                "text_only": "Text-only context",
                "with_table": "Table in context",
                "with_image": "Image in context",
            }
            for key, title in labels.items():
                block = by_mod.get(key)
                if not isinstance(block, dict):
                    continue
                rc = block.get("row_count")
                f1 = block.get("avg_answer_f1")
                g = block.get("avg_groundedness_score")
                records.append(
                    {
                        "context": title,
                        "rows": int(rc) if rc is not None else 0,
                        "avg_answer_f1": float(f1) if f1 is not None else None,
                        "avg_groundedness_score": float(g) if g is not None else None,
                    }
                )
            if records:
                st.dataframe(pd.DataFrame(records), use_container_width=True, hide_index=True)

                usage_chart_df = pd.DataFrame(
                    [
                        {
                            "modality": "Table usage",
                            "rate": float(multimodal_metrics.get("table_usage_rate") or 0.0),
                        },
                        {
                            "modality": "Image usage",
                            "rate": float(multimodal_metrics.get("image_usage_rate") or 0.0),
                        },
                        {
                            "modality": "Mixed prompt (≥2 types)",
                            "rate": float(multimodal_metrics.get("multimodal_answers_rate") or 0.0),
                        },
                    ]
                )
                bar = (
                    alt.Chart(usage_chart_df)
                    .mark_bar()
                    .encode(
                        x=alt.X("rate:Q", title="Share of rows", axis=_FLOAT_AXIS_2DP),
                        y=alt.Y("modality:N", title="", sort="-x"),
                    )
                )
                st.altair_chart(bar, use_container_width=True)

                f1_chart_records: list[dict[str, Any]] = []
                for r in records:
                    if r["avg_answer_f1"] is not None:
                        f1_chart_records.append(
                            {"bucket": r["context"], "avg_answer_f1": r["avg_answer_f1"]}
                        )
                if f1_chart_records:
                    st.caption("Average gold answer F1 by context (where gold answers exist).")
                    f1df = pd.DataFrame(f1_chart_records)
                    f1_chart = (
                        alt.Chart(f1df)
                        .mark_bar()
                        .encode(
                            x=alt.X("avg_answer_f1:Q", title="Avg answer F1", axis=_FLOAT_AXIS_2DP),
                            y=alt.Y("bucket:N", title="", sort="-x"),
                        )
                    )
                    st.altair_chart(f1_chart, use_container_width=True)


def _render_advanced_analytics(rows: list[dict], *, widget_key_prefix: str) -> None:
    with section_card(
        title="📊 Advanced Analytics",
        subtitle="Score distributions, trends across queries, hallucination signal, and pairwise metric relationships.",
        min_height=0,
    ):
        if not rows:
            st.caption("No rows available for charts.")
            return

        df = pd.DataFrame(rows)
        if df.empty:
            st.caption("No rows available for charts.")
            return

        min_groundedness = st.slider(
            "Minimum groundedness (filters analytics below)",
            min_value=0.0,
            max_value=1.0,
            value=0.0,
            step=0.05,
            help="Rows below this groundedness score are excluded from charts in this section.",
            key=f"{widget_key_prefix}_min_groundedness",
        )

        g_series = _numeric_series(df, "groundedness_score")
        if g_series is not None:
            keep = g_series.isna() | (g_series >= min_groundedness)
            df = df.loc[keep].reset_index(drop=True)
        elif min_groundedness > 0:
            st.caption("Groundedness scores unavailable; threshold filter ignored.")

        if df.empty:
            st.caption("No rows left after applying filters.")
            return

        sort_choice = st.selectbox(
            "Sort analytics preview",
            options=["dataset order", "groundedness ↓", "confidence ↓", "hallucination score ↑"],
            key=f"{widget_key_prefix}_sort_analytics",
        )
        preview = df.copy()
        gs = _numeric_series(preview, "groundedness_score")
        conf = _numeric_series(preview, "confidence")
        hal = _numeric_series(preview, "hallucination_score")
        if sort_choice == "groundedness ↓" and gs is not None:
            preview = preview.assign(_g=gs).sort_values("_g", ascending=False).drop(columns=["_g"])
        elif sort_choice == "confidence ↓" and conf is not None:
            preview = preview.assign(_c=conf).sort_values("_c", ascending=False).drop(columns=["_c"])
        elif sort_choice == "hallucination score ↑" and hal is not None:
            preview = preview.assign(_h=hal).sort_values("_h", ascending=True).drop(columns=["_h"])

        csv_bytes = preview.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download filtered rows (CSV)",
            data=csv_bytes,
            file_name="benchmark_analytics_rows.csv",
            mime="text/csv",
            use_container_width=True,
            key=f"{widget_key_prefix}_download_filtered_csv",
        )

        st.markdown("##### Score distributions")
        h1, h2, h3 = st.columns(3)
        with h1:
            _histogram_bar_chart(
                "Groundedness",
                _numeric_series(df, "groundedness_score"),
            )
        with h2:
            _histogram_bar_chart(
                "Answer F1 (gold)",
                _numeric_series(df, "answer_f1"),
            )
        with h3:
            _histogram_bar_chart(
                "Answer relevance",
                _numeric_series(df, "answer_relevance_score"),
            )
        h4, h5, h6 = st.columns(3)
        with h4:
            _histogram_bar_chart("Hallucination score", _numeric_series(df, "hallucination_score"))
        with h5:
            _histogram_bar_chart("Confidence", _numeric_series(df, "confidence"))
        with h6:
            _histogram_bar_chart(
                "Semantic similarity (gold)",
                _numeric_series(df, "semantic_similarity"),
            )
        h7, h8, _ = st.columns(3)
        with h7:
            _histogram_bar_chart("NDCG@K", _numeric_series(df, "ndcg_at_k"))
        with h8:
            _histogram_bar_chart(
                "Answer correctness",
                _numeric_series(df, "answer_correctness_score"),
            )

        st.markdown("##### Trends by query index")
        trend_parts: dict[str, pd.Series] = {}
        for label, candidates in (
            ("groundedness_score", ("groundedness_score",)),
            ("answer_relevance_score", ("answer_relevance_score",)),
            ("confidence", ("confidence",)),
        ):
            s = _numeric_series(df, *candidates)
            if s is not None:
                trend_parts[label] = s
        if trend_parts:
            trend_df = pd.DataFrame(trend_parts)
            trend_df.index = range(len(trend_df))
            tdf = trend_df.reset_index().rename(columns={"index": "query_index"})
            long_df = tdf.melt(
                id_vars="query_index", var_name="metric", value_name="value"
            )
            trend_chart = (
                alt.Chart(long_df)
                .mark_line()
                .encode(
                    x=alt.X("query_index:Q", title="Query index", axis=_INT_AXIS),
                    y=alt.Y("value:Q", title="Score", axis=_FLOAT_AXIS_2DP),
                    color=alt.Color("metric:N"),
                )
            )
            st.altair_chart(trend_chart, use_container_width=True)
        else:
            st.caption("No trend columns available.")

        st.markdown("##### Hallucination signal")
        st.caption(
            "Counts below use judge-valid rows only (judge-failed rows are excluded). "
            "That exclusion is intentional so operational judge outages are never mixed into hallucination tallies."
        )
        if "has_hallucination" in df.columns:
            hall_df = _dataframe_judge_valid_for_hallucination(df)
            if hall_df.empty:
                st.caption("No judge-valid rows in this filtered slice.")
            else:
                hall_mask = hall_df["has_hallucination"].map(_coerce_hallucination_flag)
                n_flagged = int(hall_mask.sum())
                n_total = len(hall_df)
                ratio = (n_flagged / n_total) if n_total else 0.0
                m1, m2 = st.columns(2)
                with m1:
                    render_metric_with_help(
                        label="Flagged rows",
                        value=n_flagged,
                        metric_key="hallucination_flagged_rows",
                    )
                with m2:
                    render_metric_with_help(
                        label="Flagged share",
                        value=f"{ratio * 100:.1f}%",
                        metric_key="hallucination_flagged_share",
                    )
                counts = pd.Series(
                    {"Not flagged": int((~hall_mask).sum()), "Flagged": n_flagged},
                    name="rows",
                )
                st.bar_chart(counts.to_frame())
        else:
            st.caption("No has_hallucination column in results.")

        st.markdown("##### Comparative views")
        g2 = _numeric_series(df, "groundedness_score")
        c2 = _numeric_series(df, "confidence")
        if g2 is not None and c2 is not None:
            scatter = pd.DataFrame({"confidence": c2, "groundedness_score": g2}).dropna()
            if len(scatter) >= 1:
                st.caption("Confidence vs groundedness")
                sc_chart = (
                    alt.Chart(scatter)
                    .mark_circle()
                    .encode(
                        x=alt.X("confidence:Q", axis=_FLOAT_AXIS_2DP),
                        y=alt.Y("groundedness_score:Q", axis=_FLOAT_AXIS_2DP),
                    )
                )
                st.altair_chart(sc_chart, use_container_width=True)
            else:
                st.caption("Not enough paired confidence / groundedness points.")
        else:
            st.caption("Confidence vs groundedness: missing columns.")

        rel = _numeric_series(df, "answer_relevance_score")
        g3 = _numeric_series(df, "groundedness_score")
        if rel is not None and g3 is not None:
            scatter2 = pd.DataFrame({"groundedness_score": g3, "answer_relevance_score": rel}).dropna()
            if len(scatter2) >= 1:
                st.caption("Answer relevance vs groundedness (judge scores)")
                sc2_chart = (
                    alt.Chart(scatter2)
                    .mark_circle()
                    .encode(
                        x=alt.X("groundedness_score:Q", axis=_FLOAT_AXIS_2DP),
                        y=alt.Y("answer_relevance_score:Q", axis=_FLOAT_AXIS_2DP),
                    )
                )
                st.altair_chart(sc2_chart, use_container_width=True)
            else:
                st.caption("Not enough paired groundedness / relevance points.")
        else:
            st.caption("Groundedness vs relevance: missing columns.")


def _render_health_overview(
    summary: dict,
    rows: list[dict],
    failures: dict[str, Any] | None,
) -> None:
    n = int(summary.get("total_entries") or len(rows) or 0)
    if n <= 0:
        return
    
    with section_card(
        title="System health overview",
        subtitle="Run-wide hallucination flag rate and heuristic retrieval / relevance failure shares.",
        min_height=0,
    ):
        fail_payload = failures if isinstance(failures, dict) and failures else None
        if fail_payload is None and rows:
            full = FailureAnalysisService().analyze(list(rows))
            fail_payload = {k: v for k, v in full.items() if k != "row_failures"}
        counts = fail_payload.get("counts") if isinstance(fail_payload, dict) else None
        if not isinstance(counts, dict):
            counts = {}

        def _pct(count: int) -> str:
            return f"{100.0 * float(count) / float(n):.1f}%"

        h1, h2, h3 = st.columns(3)
        hr = _coerce_float(summary.get("hallucination_rate"))
        with h1:
            st.metric(
                "Hallucination flag rate",
                f"{hr * 100:.1f}%" if hr is not None else "—",
                help="Share of judge-valid rows where has_hallucination is true (excludes judge-failed rows; same as summary).",
            )
        with h2:
            st.metric(
                "Retrieval failure (heuristic)",
                _pct(int(counts.get("retrieval_failure", 0) or 0)),
                help="Rows tagged retrieval_failure by failure analysis rules.",
            )
        with h3:
            st.metric(
                "Low relevance (heuristic)",
                _pct(int(counts.get("low_relevance", 0) or 0)),
                help="Rows tagged low_relevance by failure analysis rules.",
            )


def _comparison_sample_captions(df: pd.DataFrame, heading: str, *, suffix: str = "") -> None:
    if df.empty:
        return
    st.markdown(heading)
    for _, row in df.head(5).iterrows():
        st.caption(f"{row['metric']}: Δ = {row['delta']}{suffix}")


def _render_benchmark_comparison(
    comparison: list[dict[str, Any]] | None,
    failure_comparison: list[dict[str, Any]] | None,
) -> None:
    if comparison is None and failure_comparison is None:
        return
    with section_card(
        title="Benchmark comparison (A vs B)",
        subtitle="Metric deltas (B − A) and failure-count deltas from selected session history.",
        min_height=0,
    ):
        st.caption(
            "All numeric deltas are **B − A**. For most metrics, a **positive** delta means B is higher "
            "(usually better). For **latency**, **pipeline failure rate**, and **hallucination rate**, "
            "**lower** values are better — a **negative** delta there means B improved."
        )
        if comparison is not None:
            df = pd.DataFrame(comparison)
            if df.empty:
                st.caption("No overlapping numeric metrics between the two summaries.")
            else:
                st.dataframe(df, use_container_width=True, hide_index=True)
                critical = df[df["direction"] == "critical_regression"]
                if not critical.empty:
                    for _, row in critical.iterrows():
                        st.error(
                            f"Critical regression: **{row['metric']}** fell by {abs(float(row['delta'])):.4f} "
                            f"(large drop vs baseline A on a core quality metric; delta = B − A)."
                        )
                improved = df[df["direction"] == "improved"]
                regressed = df[df["direction"] == "regressed"]
                lo_improved = improved[improved["metric"].isin(LOWER_IS_BETTER_METRICS)]
                hi_improved = improved[~improved["metric"].isin(LOWER_IS_BETTER_METRICS)]
                lo_regressed = regressed[regressed["metric"].isin(LOWER_IS_BETTER_METRICS)]
                hi_regressed = regressed[~regressed["metric"].isin(LOWER_IS_BETTER_METRICS)]
                _comparison_sample_captions(
                    hi_improved, "**Improvements — higher is better (sample)**"
                )
                _comparison_sample_captions(
                    lo_improved,
                    "**Improvements — lower is better (sample)**",
                    suffix=" (negative means B is lower than A)",
                )
                _comparison_sample_captions(
                    hi_regressed, "**Regressions — higher is better (sample)**"
                )
                _comparison_sample_captions(
                    lo_regressed,
                    "**Regressions — lower is better (sample)**",
                    suffix=" (positive means more failures/slower/more flags in B)",
                )
        if failure_comparison is not None:
            fdf = pd.DataFrame(failure_comparison)
            if not fdf.empty:
                st.markdown("**Failure tag counts**")
                deltas = pd.to_numeric(fdf["delta"], errors="coerce").fillna(0)
                if deltas.eq(0).all():
                    st.success("Failure-tag counts match between A and B — no shift in heuristic failure labels.")
                else:
                    st.caption(
                        "Δ = (rows tagged in **B**) − (rows tagged in **A**). **Positive Δ** means that label "
                        "appeared on more rows in B."
                    )
                    st.dataframe(fdf, use_container_width=True, hide_index=True)


def _render_auto_debug(auto_debug: list[dict[str, str]] | None) -> None:
    if not auto_debug:
        return
    with section_card(
        title="Auto-debug suggestions",
        subtitle="System-level recommendations based on this evaluation run (rule-based).",
        min_height=0,
    ):
        st.caption(
            "Rule-based hints from this run’s metrics and failure tags — use as a starting point when tuning "
            "retrieval, prompting, or generation."
        )
        for item in auto_debug:
            title = item.get("title")
            desc = item.get("description")
            if title:
                st.markdown(f"**{title}**")
            if desc:
                st.caption(desc)


def render_evaluation_dashboard(
    summary: dict,
    rows: list[dict],
    *,
    widget_key_prefix: str = "benchmark_dashboard",
    correlations: dict[str, Any] | None = None,
    failures: dict[str, Any] | None = None,
    multimodal_metrics: dict[str, Any] | None = None,
    auto_debug: list[dict[str, str]] | None = None,
    comparison: list[dict[str, Any]] | None = None,
    failure_comparison: list[dict[str, Any]] | None = None,
) -> None:
    """
    Main benchmark layout. Section order is intentional and mirrors ``BenchmarkMetricFamily``:

    1. Run comparison (session A vs B) — above the fold when present
    2. Auto-debug, health overview
    3. Retrieval (ranked doc IDs), retrieval (sources), pipeline performance
    4. Gold answer overlap, prompt doc-ID overlap, answer citation overlap
    5. LLM judge aggregates, optional multimodal card, per-entry table
    6. Correlation matrix, failure analysis, advanced analytics, hallucination insights
    """
    inject_section_card_styles()

    _render_benchmark_comparison(comparison, failure_comparison)

    if not summary and not rows:
        if comparison is None and failure_comparison is None:
            st.info("Run evaluation to see results.")
        return

    _render_auto_debug(auto_debug)
    _render_health_overview(summary, rows, failures)

    has_exp_docs = int(summary.get("entries_with_expected_doc_ids") or 0) > 0
    has_exp_answers = int(summary.get("entries_with_expected_answers") or 0) > 0
    has_exp_sources = int(summary.get("entries_with_expected_sources") or 0) > 0

    with section_card(
        title="Retrieval — ranked doc IDs",
        subtitle="Overlap and ranking quality vs gold expected_doc_ids (same K as your retrieval settings).",
        min_height=0,
    ):
        if not has_exp_docs:
            st.caption("No gold expected_doc_ids in this dataset — ranked-doc metrics are not applicable (—).")
        r1, r2, r3 = st.columns(3)
        with r1:
            _summary_metric(summary, "avg_recall_at_k", "Avg recall@K")
        with r2:
            _summary_metric(summary, "avg_precision_at_k", "Avg precision@K")
        with r3:
            _summary_metric(summary, "hit_at_k", "Hit@K rate", as_percent=True)
        r4, r5, r6 = st.columns(3)
        with r4:
            _summary_metric(summary, "avg_reciprocal_rank", "Avg reciprocal rank")
        with r5:
            _summary_metric(summary, "avg_average_precision", "Avg average precision")
        with r6:
            _summary_metric(summary, "avg_ndcg_at_k", "Avg NDCG (ranked docs)")

    with section_card(
        title="Retrieval — sources",
        subtitle="Expected source paths vs sources present in retrieval or prompt context.",
        min_height=0,
    ):
        if not has_exp_sources:
            st.caption("No gold expected_sources — source recall metrics are not applicable (—).")
        s1, s2 = st.columns(2)
        with s1:
            _summary_metric(summary, "avg_source_recall", "Avg source recall")
        with s2:
            _summary_metric(summary, "source_hit_rate", "Source hit rate", as_percent=True)

    with section_card(
        title="Answer pipeline performance",
        subtitle="Latency and model confidence averaged across successful queries.",
        min_height=0,
    ):
        p1, p2, p3 = st.columns(3)
        with p1:
            _summary_metric(summary, "avg_latency_ms", "Avg latency (ms)")
        with p2:
            _summary_metric(summary, "avg_confidence", "Avg confidence")
        with p3:
            _summary_metric(
                summary, "pipeline_failure_rate", "Pipeline failure rate", as_percent=True
            )

    with section_card(
        title="Gold answer overlap",
        subtitle="Token F1 between generated answers and expected answers (where gold text exists).",
        min_height=0,
    ):
        g1, g2 = st.columns(2)
        with g1:
            _summary_metric(summary, "avg_answer_f1", "Avg answer F1")
        with g2:
            _summary_metric(summary, "avg_semantic_similarity", "Avg semantic similarity")

    with section_card(
        title="Prompt selection (doc IDs in context)",
        subtitle="All distinct doc IDs attached as prompt sources vs expected_doc_ids.",
        min_height=0,
    ):
        if not has_exp_docs:
            st.caption("No gold expected_doc_ids — prompt doc ID overlap metrics are not applicable (—).")
        pr1, pr2, pr3, pr4 = st.columns(4)
        with pr1:
            _summary_metric(summary, "avg_prompt_doc_id_precision", "Prompt doc ID P")
        with pr2:
            _summary_metric(summary, "avg_prompt_doc_id_recall", "Prompt doc ID R")
        with pr3:
            _summary_metric(summary, "avg_prompt_doc_id_f1", "Prompt doc ID F1")
        with pr4:
            _summary_metric(summary, "prompt_doc_id_hit_rate", "Prompt doc ID hit rate", as_percent=True)

    with section_card(
        title="Answer citation overlap",
        subtitle="Doc IDs inferred from [Source N] in the final answer vs expected_doc_ids.",
        min_height=0,
    ):
        if not has_exp_docs:
            st.caption("No gold expected_doc_ids — citation doc ID metrics are not applicable (—).")
        ci1, ci2, ci3, ci4 = st.columns(4)
        with ci1:
            _summary_metric(summary, "avg_citation_doc_id_precision", "Citation doc ID P")
        with ci2:
            _summary_metric(summary, "avg_citation_doc_id_recall", "Citation doc ID R")
        with ci3:
            _summary_metric(summary, "avg_citation_doc_id_f1", "Citation doc ID F1")
        with ci4:
            _summary_metric(summary, "citation_doc_id_hit_rate", "Citation doc ID hit rate", as_percent=True)

    with section_card(
        title="LLM judge",
        subtitle="Model-assessed grounding, citation use, relevance, correctness, and hallucination signals (0–1 scores where configured).",
        min_height=0,
    ):
        st.caption(
            "Summary averages and hallucination rate include only rows where the judge succeeded "
            "(rows with judge failures are excluded from these aggregates)."
        )
        if not has_exp_answers:
            st.caption("Avg answer correctness is N/A without gold answers; other judge scores still reflect this run.")
        j1, j2, j3 = st.columns(3)
        with j1:
            _summary_metric(summary, "avg_groundedness_score", "Avg groundedness")
        with j2:
            _summary_metric(summary, "avg_citation_faithfulness_score", "Avg citation faithfulness")
        with j3:
            _summary_metric(summary, "avg_answer_relevance_score", "Avg answer relevance")
        j4, j5, j6 = st.columns(3)
        with j4:
            _summary_metric(summary, "avg_answer_correctness", "Avg answer correctness")
        with j5:
            _summary_metric(summary, "avg_hallucination_score", "Avg hallucination score")
        with j6:
            _summary_metric(summary, "hallucination_rate", "Hallucination flag rate", as_percent=True)

    if multimodal_metrics:
        _render_multimodal_performance(multimodal_metrics)

    with section_card(
        title="Per-entry results",
        subtitle="One row per dataset question with retrieval metrics and judge scores.",
        min_height=0,
    ):
        st.caption(
            "Blank judge columns mean **not scored** (the judge failed for that row), **not** a score of zero. "
            "Retrieval and deterministic overlap columns may still be populated. Open **Entries** for banners and context."
        )
        if not rows:
            st.caption("Run evaluation to see per-entry rows.")
        else:
            st.dataframe(rows, use_container_width=True)

    _render_correlation_analysis(correlations, rows)

    _render_failure_analysis(failures, rows)

    _render_advanced_analytics(rows, widget_key_prefix=widget_key_prefix)

    hallucination_rows = [r for r in rows if _row_hallucination_flag(r)]
    with section_card(
        title="Hallucination insights",
        subtitle="Entries flagged by the judge as likely unsupported by retrieved evidence.",
        min_height=0,
        danger=bool(hallucination_rows),
    ):
        st.caption(
            "Only rows with successful judge scoring appear here; judge-failed rows are never listed as hallucinations. "
            "We exclude judge-failed rows on purpose so an outage of the judge model cannot inflate or distort "
            "hallucination views."
        )
        if not rows:
            st.caption("No rows to inspect.")
        elif not hallucination_rows:
            st.success("No hallucinations flagged for this run.")
        else:
            view_tag = (
                "dataset metrics"
                if widget_key_prefix.startswith("dataset_")
                else "analysis"
            )
            for idx, row in enumerate(hallucination_rows):
                q = row.get("question") or "—"
                score = _coerce_float(row.get("hallucination_score"))
                score_label = f"{score:.2f}" if score is not None else "—"
                eid = row.get("entry_id", idx)
                with st.expander(
                    f"#{eid} — score {score_label} · {view_tag}",
                    expanded=False,
                ):
                    st.markdown("**Question**")
                    st.write(q)
                    ans = _row_answer_text(row)
                    if ans:
                        st.markdown("**Answer**")
                        st.write(ans)
                    else:
                        st.caption("No answer text available for this row.")
                    render_metric_with_help(
                        label="Hallucination score",
                        value=score if score is not None else "—",
                        metric_key="hallucination_score",
                    )
