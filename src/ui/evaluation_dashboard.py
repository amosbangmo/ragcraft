"""
Unified benchmark dashboard: retrieval metrics, LLM-judge scores, per-row table, hallucination highlights.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

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
        st.metric(label, "—")
        return
    if as_percent:
        st.metric(label, f"{num * 100:.1f}%")
    else:
        st.metric(label, num)


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
    chart_df = pd.DataFrame({"count": counts.astype(int)}, index=mids)
    st.bar_chart(chart_df)


def _render_advanced_analytics(rows: list[dict]) -> None:
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
            st.line_chart(trend_df)
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
                st.metric("Flagged rows", n_flagged)
            with m2:
                st.metric("Flagged share", f"{ratio * 100:.1f}%")
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
                st.scatter_chart(scatter, x="confidence", y="groundedness_score")
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
                st.caption("Answer relevance vs citation faithfulness")
                st.scatter_chart(
                    scatter2,
                    x="citation_faithfulness_score",
                    y="answer_relevance_score",
                )
            else:
                st.caption("Not enough paired relevance / faithfulness points.")
        else:
            st.caption("Relevance vs faithfulness: missing columns.")


def render_evaluation_dashboard(summary: dict, rows: list[dict]) -> None:
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

    with section_card(
        title="Per-entry results",
        subtitle="One row per dataset question with retrieval metrics and judge scores.",
        min_height=0,
    ):
        if not rows:
            st.caption("No per-entry rows returned for this run.")
        else:
            st.dataframe(rows, use_container_width=True)

    _render_advanced_analytics(rows)

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
            for idx, row in enumerate(hallucination_rows):
                q = row.get("question") or "—"
                score = _coerce_float(row.get("hallucination_score"))
                score_label = f"{score:.2f}" if score is not None else "—"
                with st.expander(f"#{row.get('entry_id', idx)} — score {score_label}", expanded=False):
                    st.markdown("**Question**")
                    st.write(q)
                    ans = _row_answer_text(row)
                    if ans:
                        st.markdown("**Answer**")
                        st.write(ans)
                    else:
                        st.caption("No answer text available for this row.")
                    st.metric("Hallucination score", score if score is not None else "—")
