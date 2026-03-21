from __future__ import annotations

import streamlit as st

from src.domain.manual_evaluation_result import ManualEvaluationResult
from src.ui.confidence_display import format_confidence_with_band
from src.ui.raw_assets import render_raw_assets
from src.ui.source_citations import render_source_citations


def _fmt_float(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.2f}"


def _fmt_bool(value: bool | None) -> str:
    if value is None:
        return "—"
    return "Yes" if value else "No"


def _metric_row(items: list[tuple[str, str]]) -> None:
    cols = st.columns(len(items))
    for col, (label, display) in zip(cols, items):
        with col:
            st.metric(label, display)


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
            f"Groundedness **{_fmt_float(aq.groundedness_score)}** — open the **Questions** tab "
            "for citations, retrieval metrics, and expected vs retrieved."
        )
    else:
        st.caption("Open the **Questions** tab for structured quality, citations, and retrieval signals.")


def render_manual_evaluation_result(
    result: ManualEvaluationResult,
    *,
    raw_assets_collapsed: bool = False,
    include_raw_assets: bool = True,
) -> None:
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
        st.metric("Confidence", format_confidence_with_band(float(result.confidence)))

    st.caption("Citations summary")
    render_source_citations(result.citations)
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
                ("Confidence", format_confidence_with_band(float(aq.confidence))),
                ("Groundedness", _fmt_float(aq.groundedness_score)),
                ("Answer relevance", _fmt_float(aq.answer_relevance_score)),
            ]
        )
        _metric_row(
            [
                ("Hallucination score (↑ better)", _fmt_float(aq.hallucination_score)),
                ("Has hallucination", _fmt_bool(aq.has_hallucination)),
                ("Exact match (gold)", _fmt_float(aq.answer_exact_match)),
            ]
        )
        _metric_row(
            [
                ("Answer precision (gold)", _fmt_float(aq.answer_precision)),
                ("Answer recall (gold)", _fmt_float(aq.answer_recall)),
                ("Answer F1 (gold)", _fmt_float(aq.answer_f1)),
            ]
        )
        st.markdown("</div>", unsafe_allow_html=True)

    cq = result.citation_quality
    if cq:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Citation quality</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="card-subtitle">Overlap between cited assets and expected doc_ids / sources when provided.</div>',
            unsafe_allow_html=True,
        )
        _metric_row(
            [
                ("Citation doc_id P", _fmt_float(cq.citation_doc_id_precision)),
                ("Citation doc_id R", _fmt_float(cq.citation_doc_id_recall)),
                ("Citation doc_id F1", _fmt_float(cq.citation_doc_id_f1)),
            ]
        )
        _metric_row(
            [
                ("Citation source P", _fmt_float(cq.citation_source_precision)),
                ("Citation source R", _fmt_float(cq.citation_source_recall)),
                ("Citation source F1", _fmt_float(cq.citation_source_f1)),
            ]
        )
        _metric_row(
            [
                ("Citation faithfulness", _fmt_float(cq.citation_faithfulness_score)),
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
                ("Doc_id recall", _fmt_float(rq.doc_id_recall)),
                ("Source recall", _fmt_float(rq.source_recall)),
                ("Precision@K", _fmt_float(rq.precision_at_k)),
            ]
        )
        _metric_row(
            [
                ("Reciprocal rank", _fmt_float(rq.reciprocal_rank)),
                ("Average precision", _fmt_float(rq.average_precision)),
                ("Retrieved doc_ids", str(rq.retrieved_doc_ids_count)),
            ]
        )
        _metric_row(
            [
                ("Distinct cited sources", str(rq.selected_source_count)),
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
                ("Confidence", format_confidence_with_band(float(ps.confidence))),
                ("Latency (ms)", f"{ps.latency_ms:.1f}"),
                ("Retrieval mode", ps.retrieval_mode),
            ]
        )
        _metric_row(
            [
                ("Query rewrite", "On" if ps.query_rewrite_enabled else "Off"),
                ("Hybrid retrieval", "On" if ps.hybrid_retrieval_enabled else "Off"),
            ]
        )
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
            elif issue in {"Hallucination detected", "Low groundedness", "Low answer relevance"}:
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
                st.caption("Missing (expected but not cited)")
                st.code("\n".join(comp.missing_sources) or "—", language="text")
                st.caption("Retrieved / cited (order preserved)")
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
