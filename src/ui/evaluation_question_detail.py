"""
Per-question inspection: manual evaluation and single benchmark rows.
"""

from __future__ import annotations

import streamlit as st

from src.domain.manual_evaluation_result import ManualEvaluationResult
from src.ui.manual_evaluation import render_manual_evaluation_result
from src.ui.section_card import inject_section_card_styles, section_card


def render_evaluation_question_detail(result: ManualEvaluationResult) -> None:
    """Structured manual evaluation with raw evidence collapsed by default."""
    inject_section_card_styles()
    render_manual_evaluation_result(result, raw_assets_collapsed=True)


def _f(value: object) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def render_benchmark_row_detail(row: dict) -> None:
    """One benchmark dataset row, grouped like the manual evaluation layout."""
    inject_section_card_styles()
    q = row.get("question") or "—"
    st.markdown(f"**Dataset entry** #{row.get('entry_id', '—')}")
    st.write(q)

    with section_card(
        title="Answer",
        subtitle="Generated preview for this dataset question.",
        min_height=0,
    ):
        preview = row.get("answer_preview") or row.get("answer") or "—"
        st.write(preview)

    with section_card(
        title="Answer quality",
        subtitle="Judge scores and overlap with an expected answer when configured.",
        min_height=0,
    ):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Groundedness", _f(row.get("groundedness_score", row.get("groundedness"))))
        with c2:
            st.metric("Answer relevance", _f(row.get("answer_relevance_score", row.get("answer_relevance"))))
        with c3:
            st.metric("Hallucination score", _f(row.get("hallucination_score")))
        c4, c5, c6 = st.columns(3)
        with c4:
            st.metric("Has hallucination", _f(row.get("has_hallucination")))
        with c5:
            st.metric("Answer F1 (gold)", _f(row.get("answer_f1")))
        with c6:
            st.metric("Exact match (gold)", _f(row.get("answer_exact_match")))

    with section_card(
        title="Citation quality",
        subtitle="Citation-level overlap with expected doc IDs and sources.",
        min_height=0,
    ):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Citation doc ID F1", _f(row.get("citation_doc_id_f1")))
        with c2:
            st.metric("Citation doc ID recall", _f(row.get("citation_doc_id_recall")))
        with c3:
            st.metric("Citation faithfulness", _f(row.get("citation_faithfulness_score", row.get("citation_faithfulness"))))
        c4, c5, c6 = st.columns(3)
        with c4:
            st.metric("Citation source F1", _f(row.get("citation_source_f1")))
        with c5:
            st.metric("Citation source recall", _f(row.get("citation_source_recall")))
        with c6:
            st.metric("Cited doc IDs", _f(row.get("cited_doc_ids_count")))

    with section_card(
        title="Retrieval quality",
        subtitle="Ranked retrieval vs expected doc IDs and sources.",
        min_height=0,
    ):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Doc ID recall", _f(row.get("doc_id_recall")))
        with c2:
            st.metric("Precision@k", _f(row.get("precision_at_k")))
        with c3:
            st.metric("Source recall", _f(row.get("source_recall")))
        c4, c5 = st.columns(2)
        with c4:
            st.metric("MRR (row)", _f(row.get("reciprocal_rank")))
        with c5:
            st.metric("MAP (row)", _f(row.get("average_precision")))

    with section_card(
        title="Pipeline signals",
        subtitle="Runtime configuration and latency for this query.",
        min_height=0,
    ):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Confidence", _f(row.get("confidence")))
        with c2:
            st.metric("Latency (ms)", _f(row.get("latency_ms")))
        with c3:
            st.metric("Retrieval mode", row.get("retrieval_mode") or "—")
        c4, c5 = st.columns(2)
        with c4:
            st.metric("Query rewrite", "On" if row.get("query_rewrite_enabled") else "Off")
        with c5:
            st.metric("Hybrid retrieval", "On" if row.get("hybrid_retrieval_enabled") else "Off")

    with section_card(
        title="Detected issues",
        subtitle="Heuristic flags from judge and retrieval signals.",
        min_height=0,
    ):
        flags: list[str] = []
        if row.get("has_hallucination"):
            flags.append("Hallucination flagged by judge")
        g = row.get("groundedness_score", row.get("groundedness"))
        if isinstance(g, (int, float)) and g < 0.5:
            flags.append("Low groundedness")
        ar = row.get("answer_relevance_score", row.get("answer_relevance"))
        if isinstance(ar, (int, float)) and ar < 0.5:
            flags.append("Low answer relevance")
        dr = row.get("doc_id_recall")
        exp_n = row.get("expected_doc_ids_count") or 0
        if exp_n and isinstance(dr, (int, float)) and dr < 0.5:
            flags.append("Low doc ID recall vs expectations")
        if not flags:
            st.success("No strong issue pattern detected for this row.")
        else:
            for msg in flags:
                st.warning(msg)

    with section_card(
        title="Expected vs retrieved (counts)",
        subtitle="Aggregate overlap where gold expectations exist for this entry.",
        min_height=0,
    ):
        with st.expander("Coverage and overlap details", expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Doc IDs**")
                st.caption(f"Expected count: {row.get('expected_doc_ids_count', '—')}")
                st.caption(f"Retrieved (distinct): {row.get('retrieved_doc_ids_count', '—')}")
                st.caption(f"Overlap: {row.get('doc_id_overlap_count', '—')}")
            with c2:
                st.markdown("**Sources**")
                st.caption(f"Expected count: {row.get('expected_sources_count', '—')}")
                st.caption(f"Retrieved (distinct): {row.get('retrieved_sources_count', '—')}")
                st.caption(f"Overlap: {row.get('source_overlap_count', '—')}")

    with st.expander("Full row payload (technical)", expanded=False):
        st.json(row)
