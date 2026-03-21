"""
Per-question inspection: manual evaluation and single benchmark rows.
"""

from __future__ import annotations

import streamlit as st

from src.domain.manual_evaluation_result import ManualEvaluationResult
from src.ui.metric_help import render_metric_with_help
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


def render_benchmark_row_detail(row: dict, *, include_full_row_json_expander: bool = True) -> None:
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
        title="LLM judge (semantic)",
        subtitle="Model-assessed grounding, citation use, relevance, and hallucination signals.",
        min_height=0,
    ):
        c1, c2, c3 = st.columns(3)
        with c1:
            render_metric_with_help(
                label="Groundedness",
                value=_f(row.get("groundedness_score")),
                metric_key="groundedness_score",
            )
        with c2:
            render_metric_with_help(
                label="Citation faithfulness",
                value=_f(row.get("citation_faithfulness_score")),
                metric_key="citation_faithfulness_score",
            )
        with c3:
            render_metric_with_help(
                label="Answer relevance",
                value=_f(row.get("answer_relevance_score")),
                metric_key="answer_relevance_score",
            )
        c4, c5, c6 = st.columns(3)
        with c4:
            render_metric_with_help(
                label="Hallucination score",
                value=_f(row.get("hallucination_score")),
                metric_key="hallucination_score",
            )
        with c5:
            render_metric_with_help(
                label="Has hallucination",
                value=_f(row.get("has_hallucination")),
                metric_key="has_hallucination",
            )
        with c6:
            render_metric_with_help(
                label="Answer F1 (gold)",
                value=_f(row.get("answer_f1")),
                metric_key="answer_f1",
            )

    with section_card(
        title="Answer citation overlap (deterministic)",
        subtitle="Doc IDs from [Source N] labels in the answer vs gold expected_doc_ids.",
        min_height=0,
    ):
        c1, c2, c3 = st.columns(3)
        with c1:
            render_metric_with_help(
                label="Citation doc ID precision",
                value=_f(row.get("citation_doc_id_precision")),
                metric_key="citation_doc_id_precision",
            )
        with c2:
            render_metric_with_help(
                label="Citation doc ID recall",
                value=_f(row.get("citation_doc_id_recall")),
                metric_key="citation_doc_id_recall",
            )
        with c3:
            render_metric_with_help(
                label="Citation doc ID F1",
                value=_f(row.get("citation_doc_id_f1")),
                metric_key="citation_doc_id_f1",
            )
        c4, c5 = st.columns(2)
        with c4:
            render_metric_with_help(
                label="Cited doc IDs (answer)",
                value=_f(row.get("citation_doc_ids_count")),
                metric_key="citation_doc_ids_count",
            )
        with c5:
            render_metric_with_help(
                label="Citation overlap count",
                value=_f(row.get("citation_doc_id_overlap_count")),
                metric_key="citation_doc_id_overlap_count",
            )

    with section_card(
        title="Prompt selection overlap",
        subtitle="Distinct doc IDs present in prompt sources vs gold expected_doc_ids.",
        min_height=0,
    ):
        c1, c2, c3 = st.columns(3)
        with c1:
            render_metric_with_help(
                label="Prompt doc ID precision",
                value=_f(row.get("prompt_doc_id_precision")),
                metric_key="prompt_doc_id_precision",
            )
        with c2:
            render_metric_with_help(
                label="Prompt doc ID recall",
                value=_f(row.get("prompt_doc_id_recall")),
                metric_key="prompt_doc_id_recall",
            )
        with c3:
            render_metric_with_help(
                label="Prompt doc ID F1",
                value=_f(row.get("prompt_doc_id_f1")),
                metric_key="prompt_doc_id_f1",
            )
        c4, c5 = st.columns(2)
        with c4:
            render_metric_with_help(
                label="Prompt doc ID overlap",
                value=_f(row.get("prompt_doc_id_overlap_count")),
                metric_key="prompt_doc_id_overlap_count",
            )
        with c5:
            st.caption("Prompt metrics use every asset in context, not only labels in the answer.")

    with section_card(
        title="Retrieval quality",
        subtitle="Ranked retrieval vs expected doc IDs and sources.",
        min_height=0,
    ):
        c1, c2, c3 = st.columns(3)
        with c1:
            render_metric_with_help(
                label="Recall@K",
                value=_f(row.get("recall_at_k")),
                metric_key="recall_at_k",
            )
        with c2:
            render_metric_with_help(
                label="Precision@k",
                value=_f(row.get("precision_at_k")),
                metric_key="precision_at_k",
            )
        with c3:
            render_metric_with_help(
                label="Source recall",
                value=_f(row.get("source_recall")),
                metric_key="source_recall",
            )
        c4, c5 = st.columns(2)
        with c4:
            render_metric_with_help(
                label="MRR (row)",
                value=_f(row.get("reciprocal_rank")),
                metric_key="reciprocal_rank",
            )
        with c5:
            render_metric_with_help(
                label="MAP (row)",
                value=_f(row.get("average_precision")),
                metric_key="average_precision",
            )

    with section_card(
        title="Pipeline signals",
        subtitle="Runtime configuration and latency for this query.",
        min_height=0,
    ):
        c1, c2, c3 = st.columns(3)
        with c1:
            render_metric_with_help(
                label="Confidence",
                value=_f(row.get("confidence")),
                metric_key="confidence",
            )
        with c2:
            render_metric_with_help(
                label="Latency (ms)",
                value=_f(row.get("latency_ms")),
                metric_key="latency_ms",
            )
        with c3:
            render_metric_with_help(
                label="Retrieval mode",
                value=row.get("retrieval_mode") or "—",
                metric_key="retrieval_mode",
            )
        c4, c5 = st.columns(2)
        with c4:
            render_metric_with_help(
                label="Query rewrite",
                value="On" if row.get("query_rewrite_enabled") else "Off",
                metric_key="query_rewrite_enabled",
            )
        with c5:
            render_metric_with_help(
                label="Hybrid retrieval",
                value="On" if row.get("hybrid_retrieval_enabled") else "Off",
                metric_key="hybrid_retrieval_enabled",
            )

        if any(
            row.get(k) is not None
            for k in (
                "query_rewrite_ms",
                "retrieval_ms",
                "reranking_ms",
                "prompt_build_ms",
                "answer_generation_ms",
            )
        ):
            with st.expander("Per-stage latency (ms)", expanded=False):
                lc1, lc2, lc3 = st.columns(3)
                with lc1:
                    st.caption("Query rewrite")
                    st.write(_f(row.get("query_rewrite_ms")))
                with lc2:
                    st.caption("Retrieval")
                    st.write(_f(row.get("retrieval_ms")))
                with lc3:
                    st.caption("Reranking")
                    st.write(_f(row.get("reranking_ms")))
                lc4, lc5, _ = st.columns(3)
                with lc4:
                    st.caption("Prompt build")
                    st.write(_f(row.get("prompt_build_ms")))
                with lc5:
                    st.caption("Answer generation")
                    st.write(_f(row.get("answer_generation_ms")))

    with section_card(
        title="Detected issues",
        subtitle="Heuristic flags from judge and retrieval signals.",
        min_height=0,
    ):
        flags: list[str] = []
        if row.get("has_hallucination"):
            flags.append("Hallucination flagged by judge")
        g = row.get("groundedness_score")
        if isinstance(g, (int, float)) and g < 0.5:
            flags.append("Low groundedness")
        ar = row.get("answer_relevance_score")
        if isinstance(ar, (int, float)) and ar < 0.5:
            flags.append("Low answer relevance")
        dr = row.get("recall_at_k")
        exp_n = row.get("expected_doc_ids_count") or 0
        if exp_n and isinstance(dr, (int, float)) and dr < 0.5:
            flags.append("Low Recall@K vs expectations")
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

    if include_full_row_json_expander:
        with st.expander("Full row payload (technical)", expanded=False):
            st.json(row)
