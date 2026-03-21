"""
High-level benchmark / evaluation summary for the Evaluation page Overview mode.
"""

from __future__ import annotations

import streamlit as st

from src.ui.evaluation_dashboard import render_overview_insight_charts


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
        st.metric(label, "—")
        return
    if as_percent:
        st.metric(label, f"{num * 100:.1f}%")
    else:
        st.metric(label, num)


def _score_band(value: float | None) -> str | None:
    if value is None:
        return None
    if value >= 0.7:
        return "Good"
    if value >= 0.4:
        return "Medium"
    return "Poor"


def _collect_global_issues(summary: dict) -> list[str]:
    issues: list[str] = []
    n_expected_docs = int(_coerce_float(summary.get("entries_with_expected_doc_ids")) or 0)
    hall_rate = _coerce_float(summary.get("hallucination_rate"))
    if hall_rate is not None and hall_rate >= 0.2:
        issues.append(
            f"Hallucination rate is elevated ({hall_rate * 100:.0f}% of rows flagged). "
            "Review flagged entries in Debug or Per question."
        )

    doc_recall = _coerce_float(summary.get("avg_doc_id_recall"))
    if n_expected_docs > 0 and doc_recall is not None and doc_recall < 0.5:
        issues.append(
            "Average doc ID recall is low — expected documents are often missing from retrieval."
        )

    cite_recall = _coerce_float(summary.get("avg_citation_doc_id_recall"))
    if n_expected_docs > 0 and cite_recall is not None and cite_recall < 0.5:
        issues.append(
            "Citation overlap with expected doc IDs is weak — answers may not cite the gold sources."
        )

    rel = _coerce_float(summary.get("avg_answer_relevance"))
    if rel is not None and rel < 0.5:
        issues.append("Answer relevance (judge) is low — responses may drift from the question.")

    ground = _coerce_float(summary.get("avg_groundedness"))
    if ground is not None and ground < 0.5:
        issues.append("Groundedness is low — answers may rely on knowledge outside retrieved evidence.")

    if not issues:
        issues.append("No major red flags in aggregate metrics for this run.")

    return issues[:5]


def render_evaluation_overview(summary: dict, rows: list[dict]) -> None:
    """
    Curated benchmark summary: key metrics, one visual insight, global signals, and guidance.
    """
    st.markdown("### Benchmark quality (overview)")
    st.caption(
        "Start here for a quick read on system quality. Use **Per question** to dig into a single "
        "row, and **Debug** for tables, charts, and raw technical detail."
    )

    if not summary and not rows:
        st.info("Run **dataset evaluation** below to populate this overview.")
        return

    st.info(
        "**How to use this page:** stay on **Overview** for aggregate quality, open **Per question** "
        "to review one manual or dataset row in depth, and use **Debug** only when you need tables, "
        "charts, and raw JSON or evidence."
    )

    m1, m2, m3 = st.columns(3)
    with m1:
        _summary_metric_cell(summary, "avg_groundedness", "Avg groundedness")
        g = _coerce_float(summary.get("avg_groundedness"))
        band = _score_band(g)
        if band:
            st.caption(f"Label: **{band}** (aggregate)")
    with m2:
        _summary_metric_cell(summary, "avg_answer_relevance", "Avg answer relevance")
        r = _coerce_float(summary.get("avg_answer_relevance"))
        band = _score_band(r)
        if band:
            st.caption(f"Label: **{band}** (aggregate)")
    with m3:
        _summary_metric_cell(summary, "avg_citation_faithfulness", "Avg citation faithfulness")

    m4, m5, m6 = st.columns(3)
    with m4:
        _summary_metric_cell(summary, "avg_doc_id_recall", "Avg doc ID recall")
    with m5:
        _summary_metric_cell(summary, "avg_confidence", "Avg confidence")
    with m6:
        _summary_metric_cell(summary, "hallucination_rate", "Hallucination rate", as_percent=True)

    render_overview_insight_charts(rows)

    st.markdown("### Global signals")
    for line in _collect_global_issues(summary):
        st.markdown(f"- {line}")
