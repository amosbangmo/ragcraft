"""
Unified benchmark dashboard: retrieval metrics, LLM-judge scores, per-row table, hallucination highlights.
"""

from __future__ import annotations

from typing import Any

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from src.ui.metric_help import render_metric_with_help
from src.ui.section_card import inject_section_card_styles, section_card


def _coerce_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _summary_metric(summary: dict, key: str, label: str, *, as_percent: bool = False) -> None:
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


def _coerce_hallucination_flag(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes"}
    if isinstance(value, (int, float)):
        return bool(value)
    return False


def _row_hallucination_flag(row: dict) -> bool:
    return _coerce_hallucination_flag(row.get("has_hallucination"))


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
            "Pearson correlation (r) across rows. Answer correctness uses token **F1** vs the gold answer. "
            "Prompt-source metrics use **source-level** precision/recall. |r| ≥ 0.6 is treated as a strong linear association."
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
    from src.services.failure_analysis_service import FailureAnalysisService

    analysis = FailureAnalysisService().analyze(list(rows))
    analysis.pop("row_failures", None)
    return analysis


def _render_failure_analysis(
    failures: dict[str, Any] | None,
    rows: list[dict[str, Any]],
) -> None:
    with st.expander("Failure analysis", expanded=False):
        st.caption(
            "Heuristic tags from retrieval, judge scores, prompt-source overlap metrics, and gold answer F1. "
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
                        q = ex.get("question") or "—"
                        st.markdown("**Question**")
                        st.write(q)
                        prev = ex.get("answer_preview")
                        if isinstance(prev, str) and prev.strip():
                            st.markdown("**Answer preview**")
                            st.write(prev)
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            st.caption("doc recall / answer F1")
                            st.write(f"{ex.get('doc_id_recall', '—')} / {ex.get('answer_f1', '—')}")
                        with c2:
                            st.caption("grounded / hallucination")
                            st.write(f"{ex.get('groundedness', '—')} / {ex.get('hallucination_score', '—')}")
                        with c3:
                            st.caption("relevance / confidence")
                            st.write(f"{ex.get('answer_relevance', '—')} / {ex.get('confidence', '—')}")


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
            _numeric_series(df, "groundedness_score", "groundedness"),
        )
    with c2:
        _histogram_bar_chart(
            "Doc ID recall",
            _numeric_series(df, "doc_id_recall"),
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
            tc = multimodal_metrics.get("table_correctness")
            if tc is None:
                render_metric_with_help(
                    label="Table rows — avg answer F1",
                    value="—",
                    metric_key="table_correctness",
                )
            else:
                render_metric_with_help(
                    label="Table rows — avg answer F1",
                    value=float(tc),
                    metric_key="table_correctness",
                )
        with q2:
            ig = multimodal_metrics.get("image_groundedness")
            if ig is None:
                render_metric_with_help(
                    label="Image rows — avg groundedness",
                    value="—",
                    metric_key="image_groundedness",
                )
            else:
                render_metric_with_help(
                    label="Image rows — avg groundedness",
                    value=float(ig),
                    metric_key="image_groundedness",
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
                g = block.get("avg_groundedness")
                records.append(
                    {
                        "context": title,
                        "rows": int(rc) if rc is not None else 0,
                        "avg_answer_f1": float(f1) if f1 is not None else None,
                        "avg_groundedness": float(g) if g is not None else None,
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

        g_series = _numeric_series(df, "groundedness_score", "groundedness")
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
        gs = _numeric_series(preview, "groundedness_score", "groundedness")
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
                _numeric_series(df, "groundedness_score", "groundedness"),
            )
        with h2:
            _histogram_bar_chart(
                "Citation faithfulness",
                _numeric_series(df, "citation_faithfulness_score", "citation_faithfulness"),
            )
        with h3:
            _histogram_bar_chart(
                "Answer relevance",
                _numeric_series(df, "answer_relevance_score", "answer_relevance"),
            )
        h4, h5, _ = st.columns(3)
        with h4:
            _histogram_bar_chart("Hallucination score", _numeric_series(df, "hallucination_score"))
        with h5:
            _histogram_bar_chart("Confidence", _numeric_series(df, "confidence"))

        st.markdown("##### Trends by query index")
        trend_parts: dict[str, pd.Series] = {}
        for label, candidates in (
            ("groundedness_score", ("groundedness_score", "groundedness")),
            ("answer_relevance_score", ("answer_relevance_score", "answer_relevance")),
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
        if "has_hallucination" in df.columns:
            hall_mask = df["has_hallucination"].map(_coerce_hallucination_flag)
            n_flagged = int(hall_mask.sum())
            n_total = len(df)
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
        g2 = _numeric_series(df, "groundedness_score", "groundedness")
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

        rel = _numeric_series(df, "answer_relevance_score", "answer_relevance")
        faith = _numeric_series(df, "citation_faithfulness_score", "citation_faithfulness")
        if rel is not None and faith is not None:
            scatter2 = pd.DataFrame(
                {"citation_faithfulness_score": faith, "answer_relevance_score": rel}
            ).dropna()
            if len(scatter2) >= 1:
                st.caption("Answer relevance vs citation faithfulness (judge; uses prompt sources + context)")
                sc2_chart = (
                    alt.Chart(scatter2)
                    .mark_circle()
                    .encode(
                        x=alt.X(
                            "citation_faithfulness_score:Q",
                            axis=_FLOAT_AXIS_2DP,
                        ),
                        y=alt.Y(
                            "answer_relevance_score:Q",
                            axis=_FLOAT_AXIS_2DP,
                        ),
                    )
                )
                st.altair_chart(sc2_chart, use_container_width=True)
            else:
                st.caption("Not enough paired relevance / faithfulness points.")
        else:
            st.caption("Relevance vs faithfulness: missing columns.")


def render_evaluation_dashboard(
    summary: dict,
    rows: list[dict],
    *,
    widget_key_prefix: str = "benchmark_dashboard",
    correlations: dict[str, Any] | None = None,
    failures: dict[str, Any] | None = None,
    multimodal_metrics: dict[str, Any] | None = None,
) -> None:
    inject_section_card_styles()

    if not summary and not rows:
        st.info("No benchmark results to display yet.")
        return

    with section_card(
        title="Retrieval & ranking",
        subtitle="Aggregated deterministic metrics over the gold QA dataset.",
        min_height=0,
    ):
        r1, r2, r3, r4 = st.columns(4)
        with r1:
            _summary_metric(summary, "avg_doc_id_recall", "Avg doc_id recall")
        with r2:
            _summary_metric(summary, "avg_precision_at_k", "Avg precision@k")
        with r3:
            _summary_metric(summary, "mrr", "MRR")
        with r4:
            _summary_metric(summary, "map", "MAP")

    with section_card(
        title="Answer pipeline performance",
        subtitle="Latency and model confidence averaged across successful queries.",
        min_height=0,
    ):
        p1, p2 = st.columns(2)
        with p1:
            _summary_metric(summary, "avg_latency_ms", "Avg latency (ms)")
        with p2:
            _summary_metric(summary, "avg_confidence", "Avg confidence")

    with section_card(
        title="LLM-as-a-judge",
        subtitle="Groundedness, faithfulness, relevance, hallucination score, and flagged-row rate.",
        min_height=0,
    ):
        j1, j2, j3, j4, j5 = st.columns(5)
        with j1:
            _summary_metric(summary, "avg_groundedness", "Groundedness")
        with j2:
            _summary_metric(summary, "avg_citation_faithfulness", "Faithfulness")
        with j3:
            _summary_metric(summary, "avg_answer_relevance", "Relevance")
        with j4:
            _summary_metric(summary, "avg_hallucination_score", "Hallucination")
        with j5:
            _summary_metric(summary, "hallucination_rate", "Hallucination rate", as_percent=True)

    if multimodal_metrics:
        _render_multimodal_performance(multimodal_metrics)

    with section_card(
        title="Per-entry results",
        subtitle="One row per dataset question with retrieval metrics and judge scores.",
        min_height=0,
    ):
        if not rows:
            st.caption("No per-entry rows returned for this run.")
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
