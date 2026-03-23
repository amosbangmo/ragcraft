"""
Per-question inspection: manual evaluation and single benchmark rows.
"""

from __future__ import annotations

import streamlit as st

from components.shared.manual_evaluation import render_manual_evaluation_result
from components.shared.metric_help import render_metric_with_help
from components.shared.section_card import inject_section_card_styles, section_card
from services.api_client import ManualEvaluationResult


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


def _fmt_llm_judge_metric(row: dict, key: str) -> str:
    """Judge metrics are unavailable when ``judge_failed``; never show stub numerics."""
    if row.get("judge_failed"):
        return "—"
    return _f(row.get(key))


def render_benchmark_row_detail(row: dict, *, include_full_row_json_expander: bool = True) -> None:
    """One benchmark dataset row, grouped like the manual evaluation layout."""
    inject_section_card_styles()
    q = row.get("question") or "—"
    st.markdown(f"**Dataset entry** #{row.get('entry_id', '—')}")
    st.write(q)
    if row.get("pipeline_failed"):
        st.warning(
            "⚠️ **Pipeline failed** — the answer pipeline did not complete; retrieval and judge metrics "
            "for this row are not meaningful (shown as — where applicable)."
        )
    elif row.get("judge_failed"):
        st.info(
            "**LLM judge did not score this row** — the answer pipeline finished, but the judge call failed or "
            "returned no usable scores."
        )
        st.markdown(
            "- **Still valid here:** retrieval metrics, prompt/citation doc-ID overlap, gold answer F1, semantic "
            "similarity, latency, and pipeline signals.\n"
            "- **Not available:** judge-only scores below (shown as —); they are **missing**, not weak scores."
        )
        jr = row.get("judge_failure_reason")
        if isinstance(jr, str) and jr.strip():
            st.caption(f"**Judge failure reason:** `{jr.strip()}`")

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
        if row.get("judge_failed"):
            st.caption(
                "Judge-only metrics are **—** because the judge did not return usable values — not because they scored zero."
            )
        c1, c2, c3 = st.columns(3)
        with c1:
            render_metric_with_help(
                label="Groundedness",
                value=_fmt_llm_judge_metric(row, "groundedness_score"),
                metric_key="groundedness_score",
            )
        with c2:
            render_metric_with_help(
                label="Citation faithfulness",
                value=_fmt_llm_judge_metric(row, "citation_faithfulness_score"),
                metric_key="citation_faithfulness_score",
            )
        with c3:
            render_metric_with_help(
                label="Answer relevance",
                value=_fmt_llm_judge_metric(row, "answer_relevance_score"),
                metric_key="answer_relevance_score",
            )
        c4, c5, c6 = st.columns(3)
        with c4:
            render_metric_with_help(
                label="Answer correctness",
                value=_fmt_llm_judge_metric(row, "answer_correctness_score"),
                metric_key="answer_correctness_score",
            )
        with c5:
            render_metric_with_help(
                label="Hallucination score",
                value=_fmt_llm_judge_metric(row, "hallucination_score"),
                metric_key="hallucination_score",
            )
        with c6:
            render_metric_with_help(
                label="Has hallucination",
                value=_fmt_llm_judge_metric(row, "has_hallucination"),
                metric_key="has_hallucination",
            )
        st.caption("Gold overlap (deterministic, not from the judge)")
        c7, c8, _ = st.columns(3)
        with c7:
            render_metric_with_help(
                label="Answer F1 (gold)",
                value=_f(row.get("answer_f1")),
                metric_key="answer_f1",
            )
        with c8:
            render_metric_with_help(
                label="Semantic similarity",
                value=_f(row.get("semantic_similarity")),
                metric_key="semantic_similarity",
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
        c4, c5, c6 = st.columns(3)
        with c4:
            render_metric_with_help(
                label="Citation doc ID hit",
                value=_f(row.get("citation_doc_id_hit_rate")),
                metric_key="citation_doc_id_hit_rate",
            )
        with c5:
            render_metric_with_help(
                label="Cited doc IDs (answer)",
                value=_f(row.get("citation_doc_ids_count")),
                metric_key="citation_doc_ids_count",
            )
        with c6:
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
        c4, c5, c6 = st.columns(3)
        with c4:
            render_metric_with_help(
                label="Prompt doc ID hit",
                value=_f(row.get("prompt_doc_id_hit_rate")),
                metric_key="prompt_doc_id_hit_rate",
            )
        with c5:
            render_metric_with_help(
                label="Prompt overlap count",
                value=_f(row.get("prompt_doc_id_overlap_count")),
                metric_key="prompt_doc_id_overlap_count",
            )
        with c6:
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
                label="Precision@K",
                value=_f(row.get("precision_at_k")),
                metric_key="precision_at_k",
            )
        with c3:
            render_metric_with_help(
                label="Source recall",
                value=_f(row.get("source_recall")),
                metric_key="source_recall",
            )
        c4, c5, c6 = st.columns(3)
        with c4:
            render_metric_with_help(
                label="Reciprocal rank",
                value=_f(row.get("reciprocal_rank")),
                metric_key="reciprocal_rank",
            )
        with c5:
            render_metric_with_help(
                label="Average precision",
                value=_f(row.get("average_precision")),
                metric_key="average_precision",
            )
        with c6:
            render_metric_with_help(
                label="Hit@K",
                value=_f(row.get("hit_at_k")),
                metric_key="hit_at_k",
            )
        c7, _, _ = st.columns(3)
        with c7:
            render_metric_with_help(
                label="NDCG@K",
                value=_f(row.get("ndcg_at_k")),
                metric_key="ndcg_at_k",
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
        if row.get("judge_failed") and not row.get("pipeline_failed"):
            flags.append("LLM judge unavailable — see failure analysis “judge failure” if present")
        if not row.get("judge_failed") and row.get("has_hallucination"):
            flags.append("Hallucination flagged by judge")
        g = row.get("groundedness_score")
        if not row.get("judge_failed") and isinstance(g, (int, float)) and g < 0.5:
            flags.append("Low groundedness")
        ar = row.get("answer_relevance_score")
        if not row.get("judge_failed") and isinstance(ar, (int, float)) and ar < 0.5:
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
        title="Explainability",
        subtitle="Why this result scored the way it did and how to improve it.",
        min_height=0,
    ):
        if row.get("failure_critical"):
            st.error("High-confidence failure: investigate this case first.")
        raw_expl = row.get("explanations")
        raw_sugg = row.get("suggestions")
        if raw_expl is None and raw_sugg is None:
            st.caption(
                "Explainability hints are not stored on this row — run a fresh dataset evaluation."
            )
        else:
            explanations = list(raw_expl) if isinstance(raw_expl, list) else []
            suggestions = list(raw_sugg) if isinstance(raw_sugg, list) else []

            if not explanations:
                st.success("No major issues detected for this row.")
            else:
                st.markdown("**What likely happened**")
                for e in explanations:
                    st.write(f"- {e}")

            if suggestions:
                st.markdown("**Suggested improvements**")
                for s in suggestions:
                    st.write(f"- {s}")

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
