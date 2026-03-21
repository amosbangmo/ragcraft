"""
Central registry and helpers for metric tooltips on the Evaluation UI.

Add new metrics by extending ``METRIC_HELP`` and rendering via ``render_metric_with_help``.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

# Short tooltip copy: what it means, how to read it, and direction when obvious.
METRIC_HELP: dict[str, str] = {
    "confidence": (
        "Pipeline confidence from reranked evidence strength and consistency. "
        "Higher is usually better; compare within the same project settings."
    ),
    "avg_confidence": (
        "Mean pipeline confidence across successful dataset questions. "
        "Higher is usually better when settings are unchanged."
    ),
    "latency_ms": (
        "End-to-end time for this question (milliseconds). "
        "Lower is usually better if quality stays acceptable."
    ),
    "avg_latency_ms": (
        "Average latency per successful query in this benchmark run. "
        "Lower is usually better for the same workload."
    ),
    "recall_at_k": (
        "Share of relevant documents retrieved in the top-K results. Closer to 1 is better."
    ),
    "avg_recall_at_k": (
        "Mean recall@K across entries with expected doc_ids (same K as the evaluator). "
        "Closer to 1 is better."
    ),
    "source_recall": (
        "Share of expected source files represented in retrieval or prompt sources. "
        "Closer to 1 is better when expectations are set."
    ),
    "avg_source_recall": (
        "Average source recall across entries with expected sources. "
        "Closer to 1 is better."
    ),
    "precision_at_k": (
        "Fraction of the top-k retrieved doc IDs that are relevant (match expectations). "
        "Higher is better; depends on k used by your evaluator."
    ),
    "avg_precision_at_k": (
        "Mean precision@k over the run. Higher means denser relevant results at the top."
    ),
    "reciprocal_rank": (
        "Inverse rank of the first relevant document (1 / rank), 0 if none in the list. "
        "Higher is better."
    ),
    "mrr": (
        "Mean reciprocal rank: average of 1 / (rank of first hit). "
        "Higher is better for ranked retrieval."
    ),
    "average_precision": (
        "Average precision across ranks for relevant docs in this ranked list. "
        "Higher is better when multiple relevant items exist."
    ),
    "map": (
        "Mean average precision over questions: ranking quality when several relevant docs matter. "
        "Higher is better."
    ),
    "answer_f1": (
        "Harmonic mean of answer precision and recall vs gold. "
        "Closer to 1 is better."
    ),
    "avg_answer_f1": (
        "Mean answer F1 across rows with gold answers. Closer to 1 is better."
    ),
    "groundedness_score": (
        "Judge score: how well the answer stays supported by retrieved evidence. "
        "Closer to 1 is better."
    ),
    "avg_groundedness": (
        "Mean groundedness over the run. Closer to 1 is better."
    ),
    "citation_faithfulness_score": (
        "Judge score: whether [Source N] citations align with the claims they support. "
        "Closer to 1 is better."
    ),
    "avg_citation_faithfulness": (
        "Mean citation faithfulness over the run. Closer to 1 is better."
    ),
    "answer_relevance_score": (
        "Judge score: how well the answer addresses the question. Closer to 1 is better."
    ),
    "avg_answer_relevance": (
        "Mean answer relevance over the run. Closer to 1 is better."
    ),
    "hallucination_score": (
        "Judge signal for unsupported or contradictory content. "
        "Interpretation depends on your judge configuration—compare rows in the same run."
    ),
    "avg_hallucination_score": (
        "Mean hallucination judge signal across rows. Compare across runs with the same judge settings."
    ),
    "hallucination_rate": (
        "Fraction of rows flagged as likely hallucinating. "
        "Lower is usually better."
    ),
    "has_hallucination": (
        "Whether the judge flagged likely hallucination for this row. "
        "No is usually preferable."
    ),
    "prompt_doc_id_precision": (
        "Precision of prompt-source doc IDs vs expected doc IDs. Higher is better."
    ),
    "avg_prompt_doc_id_precision": (
        "Mean prompt doc ID precision (prompt sources vs expected). Higher is better."
    ),
    "prompt_doc_id_recall": (
        "Recall of expected doc IDs among prompt sources. Higher is better."
    ),
    "avg_prompt_doc_id_recall": (
        "Mean prompt doc ID recall (prompt sources). Higher is better."
    ),
    "prompt_doc_id_f1": (
        "F1 between prompt-source and expected doc IDs. Closer to 1 is better."
    ),
    "avg_prompt_doc_id_f1": (
        "Mean prompt doc ID F1 (prompt sources). Closer to 1 is better."
    ),
    "citation_doc_id_precision": (
        "Precision of doc IDs **cited in the answer** (via [Source N]) vs expected doc IDs. "
        "Higher is better."
    ),
    "avg_citation_doc_id_precision": (
        "Mean answer-citation doc ID precision. Higher is better."
    ),
    "citation_doc_id_recall": (
        "Recall of expected doc IDs among doc IDs cited in the answer. Higher is better."
    ),
    "avg_citation_doc_id_recall": (
        "Mean answer-citation doc ID recall. Higher is better."
    ),
    "citation_doc_id_f1": (
        "F1 between answer-cited and expected doc IDs. Closer to 1 is better."
    ),
    "avg_citation_doc_id_f1": (
        "Mean answer-citation doc ID F1. Closer to 1 is better."
    ),
    "citation_doc_id_overlap_count": (
        "Count of expected doc IDs that appear among answer citations for this row."
    ),
    "citation_doc_ids_count": (
        "Distinct doc IDs cited in the answer (parsed from [Source N] labels mapped to prompt sources)."
    ),
    "citation_doc_id_hit_rate": (
        "Share of entries with at least one expected doc ID cited in the answer. Higher is better."
    ),
    "prompt_doc_id_overlap_count": (
        "Count of expected doc IDs that also appear in prompt sources for this row."
    ),
    "retrieved_doc_ids_count": (
        "Count of distinct doc IDs returned by retrieval for this question."
    ),
    "selected_source_count": (
        "How many distinct sources were selected for the prompt for this run."
    ),
    "hit_at_k": (
        "Whether at least one relevant document appears in the top-K results. "
        "Averaged over queries. Closer to 1 is better."
    ),
    "source_hit_rate": (
        "Share of entries where at least one expected source was hit. "
        "Higher is better."
    ),
    "prompt_doc_id_hit_rate": (
        "Share of entries where prompt sources overlap expected doc IDs. Higher is better."
    ),
    "retrieval_mode": (
        "Which retrieval path ran for this query (for example vector-only vs hybrid)."
    ),
    "query_rewrite_enabled": (
        "Whether query rewrite was on for this run."
    ),
    "hybrid_retrieval_enabled": (
        "Whether dense + sparse (hybrid) retrieval was enabled."
    ),
    "hallucination_flagged_rows": (
        "Count of rows flagged as likely hallucinating in the filtered analytics slice."
    ),
    "hallucination_flagged_share": (
        "Percentage of rows flagged in that slice. Lower is usually better."
    ),
    "gold_qa_entry_count": (
        "Number of gold QA rows stored for this project."
    ),
    "dataset_entry_count": (
        "Gold QA rows in this project used for dataset evaluation."
    ),
    "evaluation_project_context": (
        "The project whose corpus and QA dataset are used on this Evaluation page."
    ),
}

_METRIC_HELP_FALLBACK = (
    "No tooltip yet for this metric; see benchmark docs or add a key in src/ui/metric_help.py."
)


def resolve_metric_help(
    *,
    metric_key: str | None,
    help_text: str | None = None,
    use_registry_fallback: bool = True,
) -> str | None:
    """
    Resolve tooltip text: explicit ``help_text`` wins, then ``METRIC_HELP[metric_key]``,
    then a short generic fallback when ``metric_key`` was supplied but unknown.
    """
    if help_text is not None:
        return help_text
    if not metric_key:
        return None
    found = METRIC_HELP.get(metric_key)
    if found is not None:
        return found
    if use_registry_fallback:
        return _METRIC_HELP_FALLBACK
    return None


def render_metric_with_help(
    *,
    label: str,
    value: Any,
    metric_key: str | None = None,
    help_text: str | None = None,
    delta: Any = None,
    delta_color: str = "normal"
) -> None:
    """
    Render ``st.metric`` with optional centralized help (tooltip).

    Supply either ``metric_key`` (looked up in ``METRIC_HELP``) or ``help_text``.
    """
    tooltip = resolve_metric_help(metric_key=metric_key, help_text=help_text)
    extra: dict[str, Any] = {}
    if tooltip is not None:
        extra["help"] = tooltip
    if delta is not None:
        extra["delta"] = delta
        extra["delta_color"] = delta_color
    st.metric(label, value, **extra)
