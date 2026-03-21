"""
Unified benchmark dashboard: retrieval metrics, LLM-judge scores, per-row table, hallucination highlights.
"""

from __future__ import annotations

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


def _row_hallucination_flag(row: dict) -> bool:
    flag = row.get("has_hallucination")
    if isinstance(flag, bool):
        return flag
    if isinstance(flag, str):
        return flag.strip().lower() in {"true", "1", "yes"}
    if isinstance(flag, (int, float)):
        return bool(flag)
    return False


def _row_answer_text(row: dict) -> str | None:
    for key in ("answer", "answer_preview", "generated_answer"):
        val = row.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


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
