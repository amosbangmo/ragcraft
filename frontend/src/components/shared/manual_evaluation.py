from __future__ import annotations

import streamlit as st

from services.view_models import JUDGE_FAILURE_REASON, ManualEvaluationResult
from components.shared.confidence_display import format_confidence_with_band
from components.shared.metric_help import render_metric_with_help
from components.shared.raw_assets import render_raw_assets
from components.shared.prompt_sources import render_prompt_sources


def _fmt_float(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.2f}"


def _fmt_bool(value: bool | None) -> str:
    if value is None:
        return "—"
    return "Yes" if value else "No"


def _metric_row(items: list[tuple[str, str, str | None]]) -> None:
    cols = st.columns(len(items))
    for col, (label, display, metric_key) in zip(cols, items):
        with col:
            render_metric_with_help(
                label=label, value=display, metric_key=metric_key
            )


def render_manual_evaluation_compact(result: ManualEvaluationResult) -> None:
    """Short summary after a manual run (Evaluation page Overview mode)."""
    st.success("Manual evaluation completed.")
    preview = (result.answer or "").strip()
    if len(preview) > 280:
        preview = preview[:280] + "…"
    st.caption("Answer preview")
    st.write(preview or "—")
    aq = result.answer_quality
    if aq and aq.groundedness_score is not None:
        st.caption(
            f"Groundedness **{_fmt_float(aq.groundedness_score)}** — scroll this tab for prompt sources, "
            "retrieval metrics, and expected vs retrieved."
        )
    else:
        st.caption("Scroll this tab for structured quality, prompt sources, and retrieval signals.")


def render_manual_evaluation_result(
    result: ManualEvaluationResult,
    *,
    raw_assets_collapsed: bool = False,
    include_raw_assets: bool = True,
) -> None:
    if result.pipeline_failed:
        st.warning(
            "Retrieval pipeline did not complete. Missing rubric fields are **unavailable**, not weak scores."
        )
    elif result.judge_failed:
        detail = ""
        if result.judge_failure_reason and result.judge_failure_reason.strip() not in (
            "",
            JUDGE_FAILURE_REASON,
        ):
            detail = f" ({result.judge_failure_reason.strip()})"
        st.info(
            f"LLM judge did not return scores{detail}. Retrieval metrics may still apply; "
            "judge rubric values show as unavailable (—), not as low grades."
        )

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Answer</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="card-subtitle">Generated response and overall confidence for this question.</div>',
        unsafe_allow_html=True,
    )

    if not (result.answer or "").strip():
        st.warning("No answer text was returned for this question.")

    c1, c2 = st.columns([3, 1])
    with c1:
        st.write(result.answer or "—")
    with c2:
        render_metric_with_help(
            label="Confidence",
            value=format_confidence_with_band(float(result.confidence)),
            metric_key="confidence",
        )

    st.caption("Sources provided to the model")
    render_prompt_sources(result.prompt_sources)
    st.markdown("</div>", unsafe_allow_html=True)

    aq = result.answer_quality
    if aq:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Answer quality</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="card-subtitle">Grounding, relevance, hallucination signals, and optional gold overlap.</div>',
            unsafe_allow_html=True,
        )
        _metric_row(
            [
                (
                    "Confidence",
                    format_confidence_with_band(float(aq.confidence)),
                    "confidence",
                ),
                ("Groundedness", _fmt_float(aq.groundedness_score), "groundedness_score"),
                (
                    "Citation faithfulness",
                    _fmt_float(aq.citation_faithfulness_score),
                    "citation_faithfulness_score",
                ),
            ]
        )
        _metric_row(
            [
                (
                    "Answer relevance",
                    _fmt_float(aq.answer_relevance_score),
                    "answer_relevance_score",
                ),
                (
                    "Answer correctness",
                    _fmt_float(aq.answer_correctness_score),
                    "answer_correctness_score",
                ),
                (
                    "Hallucination score (↑ better)",
                    _fmt_float(aq.hallucination_score),
                    "hallucination_score",
                ),
            ]
        )
        _metric_row(
            [
                ("Has hallucination", _fmt_bool(aq.has_hallucination), "has_hallucination"),
                ("Answer F1 (gold)", _fmt_float(aq.answer_f1), "answer_f1"),
                ("Semantic similarity", _fmt_float(aq.semantic_similarity), "semantic_similarity"),
            ]
        )
        st.markdown("</div>", unsafe_allow_html=True)

    acq = result.answer_citation_quality
    if acq:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Answer citation overlap</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="card-subtitle">Doc IDs cited in the answer via [Source N] labels vs expected doc_ids.</div>',
            unsafe_allow_html=True,
        )
        _metric_row(
            [
                (
                    "Citation doc_id P",
                    _fmt_float(acq.citation_doc_id_precision),
                    "citation_doc_id_precision",
                ),
                (
                    "Citation doc_id R",
                    _fmt_float(acq.citation_doc_id_recall),
                    "citation_doc_id_recall",
                ),
                (
                    "Citation doc_id F1",
                    _fmt_float(acq.citation_doc_id_f1),
                    "citation_doc_id_f1",
                ),
            ]
        )
        _metric_row(
            [
                (
                    "Cited doc IDs (count)",
                    str(acq.citation_doc_ids_count)
                    if acq.citation_doc_ids_count is not None
                    else "—",
                    "citation_doc_ids_count",
                ),
                (
                    "Overlap count",
                    str(acq.citation_doc_id_overlap_count)
                    if acq.citation_doc_id_overlap_count is not None
                    else "—",
                    "citation_doc_id_overlap_count",
                ),
            ]
        )
        st.markdown("</div>", unsafe_allow_html=True)

    cq = result.prompt_source_quality
    if cq:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Prompt source quality</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="card-subtitle">Prompt-source doc IDs vs expected doc_ids when provided.</div>',
            unsafe_allow_html=True,
        )
        _metric_row(
            [
                (
                    "Prompt doc_id P",
                    _fmt_float(cq.prompt_doc_id_precision),
                    "prompt_doc_id_precision",
                ),
                (
                    "Prompt doc_id R",
                    _fmt_float(cq.prompt_doc_id_recall),
                    "prompt_doc_id_recall",
                ),
                (
                    "Prompt doc_id F1",
                    _fmt_float(cq.prompt_doc_id_f1),
                    "prompt_doc_id_f1",
                ),
            ]
        )
        st.markdown("</div>", unsafe_allow_html=True)

    rq = result.retrieval_quality
    if rq:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Retrieval quality</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="card-subtitle">Ranked retrieval vs expectations and basic selection counts.</div>',
            unsafe_allow_html=True,
        )
        _metric_row(
            [
                ("Recall@K", _fmt_float(rq.recall_at_k), "recall_at_k"),
                ("Source recall", _fmt_float(rq.source_recall), "source_recall"),
                ("Precision@K", _fmt_float(rq.precision_at_k), "precision_at_k"),
            ]
        )
        _metric_row(
            [
                (
                    "Reciprocal rank",
                    _fmt_float(rq.reciprocal_rank),
                    "reciprocal_rank",
                ),
                (
                    "Average precision",
                    _fmt_float(rq.average_precision),
                    "average_precision",
                ),
                ("NDCG@K", _fmt_float(rq.ndcg_at_k), "ndcg_at_k"),
            ]
        )
        _metric_row(
            [
                (
                    "Retrieved doc_ids",
                    str(rq.retrieved_doc_ids_count),
                    "retrieved_doc_ids_count",
                ),
                (
                    "Distinct cited sources",
                    str(rq.selected_source_count),
                    "selected_source_count",
                ),
            ]
        )
        st.markdown("</div>", unsafe_allow_html=True)

    ps = result.pipeline_signals
    if ps:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Pipeline signals</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="card-subtitle">How this run was configured end to end.</div>',
            unsafe_allow_html=True,
        )
        _metric_row(
            [
                (
                    "Confidence",
                    format_confidence_with_band(float(ps.confidence)),
                    "confidence",
                ),
                ("Latency (ms)", f"{ps.latency_ms:.1f}", "latency_ms"),
                ("Retrieval mode", ps.retrieval_mode, "retrieval_mode"),
            ]
        )
        _metric_row(
            [
                (
                    "Query rewrite",
                    "On" if ps.query_rewrite_enabled else "Off",
                    "query_rewrite_enabled",
                ),
                (
                    "Hybrid retrieval",
                    "On" if ps.hybrid_retrieval_enabled else "Off",
                    "hybrid_retrieval_enabled",
                ),
            ]
        )
        if ps.stage_latency:
            with st.expander("Per-stage latency (ms)", expanded=False):
                sl = ps.stage_latency.to_dict()
                r1, r2, r3 = st.columns(3)
                with r1:
                    st.caption("Query rewrite")
                    st.write(f"{float(sl.get('query_rewrite_ms', 0.0)):.2f}")
                with r2:
                    st.caption("Retrieval")
                    st.write(f"{float(sl.get('retrieval_ms', 0.0)):.2f}")
                with r3:
                    st.caption("Reranking")
                    st.write(f"{float(sl.get('reranking_ms', 0.0)):.2f}")
                r4, r5, r6 = st.columns(3)
                with r4:
                    st.caption("Prompt build")
                    st.write(f"{float(sl.get('prompt_build_ms', 0.0)):.2f}")
                with r5:
                    st.caption("Answer generation")
                    st.write(f"{float(sl.get('answer_generation_ms', 0.0)):.2f}")
                with r6:
                    st.caption("Total")
                    st.write(f"{float(sl.get('total_ms', ps.latency_ms)):.2f}")
        st.markdown("</div>", unsafe_allow_html=True)

    if result.detected_issues:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Detected issues</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="card-subtitle">Rule-based flags — tune thresholds in <code>manual_evaluation_service</code>.</div>',
            unsafe_allow_html=True,
        )
        for issue in result.detected_issues:
            if issue == "No answer generated":
                st.error(issue)
            elif issue in {
                "Hallucination detected",
                "Low groundedness",
                "Low answer relevance",
                "Low prompt doc ID recall",
            }:
                st.warning(issue)
            else:
                st.info(issue)
        st.markdown("</div>", unsafe_allow_html=True)

    if result.expected_answer or result.expectation_comparison:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Expected vs retrieved</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="card-subtitle">Gold expectations you entered for this manual run.</div>',
            unsafe_allow_html=True,
        )
        if result.expected_answer:
            ec1, ec2 = st.columns(2)
            with ec1:
                st.markdown("**Expected answer**")
                st.write(result.expected_answer)
            with ec2:
                st.markdown("**Model answer**")
                st.write(result.answer or "—")

        comp = result.expectation_comparison
        if comp:
            d1, d2 = st.columns(2)
            with d1:
                st.markdown("**Doc IDs**")
                st.caption("Matched")
                st.code("\n".join(comp.matched_doc_ids) or "—", language="text")
                st.caption("Missing (expected but not retrieved)")
                st.code("\n".join(comp.missing_doc_ids) or "—", language="text")
                st.caption("Expected (full list)")
                st.code("\n".join(comp.expected_doc_ids) or "—", language="text")
            with d2:
                st.markdown("**Sources**")
                st.caption("Matched")
                st.code("\n".join(comp.matched_sources) or "—", language="text")
                st.caption("Missing (expected but not in prompt sources)")
                st.code("\n".join(comp.missing_sources) or "—", language="text")
                st.caption("Retrieved / prompt sources (order preserved)")
                st.code("\n".join(comp.retrieved_sources) or "—", language="text")
                st.caption("Expected sources (full list)")
                st.code("\n".join(comp.expected_sources) or "—", language="text")
        st.markdown("</div>", unsafe_allow_html=True)

    if not include_raw_assets:
        return

    if raw_assets_collapsed:
        with st.expander("Raw evidence (advanced)", expanded=False):
            st.caption(
                "Raw text, tables, and images passed into the prompt after reranking."
            )
            render_raw_assets(result.raw_assets, mode="evaluation")
    else:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Raw evidence</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="card-subtitle">Raw text, tables, and images passed into the prompt after reranking.</div>',
            unsafe_allow_html=True,
        )
        render_raw_assets(result.raw_assets, mode="evaluation")
        st.markdown("</div>", unsafe_allow_html=True)
