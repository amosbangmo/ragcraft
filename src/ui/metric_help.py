"""
Central registry and helpers for metric tooltips on the Evaluation UI.

Add new metrics by extending ``METRIC_HELP`` and rendering via ``render_metric_with_help``.

Tooltip copy follows a consistent structure where applicable:

1. **Measures** — what the metric quantifies
2. **Range** — scale or units (e.g. 0–1, ms, count)
3. **Interpret** — how to read it or important caveats
4. **Direction** — higher vs lower better, or “compare within same settings”
"""

from __future__ import annotations

from typing import Any

import streamlit as st

# Each value: what it measures → range → interpretation → direction (when applicable).
METRIC_HELP: dict[str, str] = {
    "confidence": (
        "Measures pipeline confidence from reranked evidence strength and consistency. "
        "Range: typically 0–1 from the pipeline (verify your build). "
        "Higher values suggest stronger agreement among retrieved signals. "
        "Higher is better; compare within the same project and settings."
    ),
    "avg_confidence": (
        "Measures mean pipeline confidence over successful benchmark rows. "
        "Range: typically 0–1 (same scale as per-row confidence). "
        "Summarizes overall retrieval/evidence strength for the run. "
        "Higher is better when configuration is unchanged."
    ),
    "latency_ms": (
        "Measures end-to-end wall time to produce the answer for this question. "
        "Range: milliseconds (non-negative). "
        "Includes retrieval, reranking, and generation as configured. "
        "Lower is better when quality is acceptable."
    ),
    "avg_latency_ms": (
        "Measures mean end-to-end latency per successful query in this run. "
        "Range: milliseconds (non-negative). "
        "Summarizes typical responsiveness for the workload. "
        "Lower is better for the same quality bar."
    ),
    "pipeline_failure_rate": (
        "Measures the share of dataset rows where the **answer pipeline** did not complete (`pipeline_failed`). "
        "Range: 0–1 (often shown as a percentage). "
        "Distinct from judge failures: rows can finish the pipeline yet fail judging. "
        "Denominator is all evaluated rows. Lower is better."
    ),
    "judge_failed": (
        "True when the answer pipeline finished but the **LLM judge** did not return usable scores. "
        "Range: boolean. "
        "Judge fields are absent (None), not zero; retrieval and deterministic overlap may still be present. "
        "Operational judge issue — not a quality score."
    ),
    "judge_failure_reason": (
        "Short machine-readable reason when `judge_failed` is true (e.g. timeout or a judge service sentinel). "
        "Range: string or empty. "
        "Use for debugging; do not map directly to answer quality. "
        "Neutral (diagnostic)."
    ),
    "recall_at_k": (
        "Measures the fraction of expected document IDs that appear in the top-K ranked list. "
        "Range: 0–1. "
        "Uses the evaluator’s K and your expected doc ID set. "
        "Higher is better (more expected docs retrieved in the window)."
    ),
    "avg_recall_at_k": (
        "Measures mean recall@K across rows that define expected doc IDs. "
        "Range: 0–1. "
        "Same K and definition as per-row recall_at_k. "
        "Higher is better."
    ),
    "source_recall": (
        "Measures the fraction of expected source files hit in retrieval or prompt sources. "
        "Range: 0–1 when expectations are set. "
        "File-level overlap, not chunk-level doc IDs. "
        "Higher is better when gold sources are defined."
    ),
    "avg_source_recall": (
        "Measures mean source recall across rows with expected sources. "
        "Range: 0–1. "
        "Aggregates file-level coverage for the run. "
        "Higher is better."
    ),
    "precision_at_k": (
        "Measures the fraction of top-K retrieved doc IDs that match expected doc IDs. "
        "Range: 0–1. "
        "Dense top-K means less noise when this is high. "
        "Higher is better."
    ),
    "avg_precision_at_k": (
        "Measures mean precision@K over the run. "
        "Range: 0–1. "
        "Indicates how often the top of the ranked list is relevant. "
        "Higher is better."
    ),
    "reciprocal_rank": (
        "Measures the inverse rank of the first expected doc in the ranked list (1/rank), or 0 if none. "
        "Range: 0–1 (1.0 only when the first hit is rank 1). "
        "Rewards placing any expected doc early. "
        "Higher is better."
    ),
    "avg_reciprocal_rank": (
        "Measures mean reciprocal rank over rows with expected doc IDs. "
        "Range: 0–1. "
        "Run-level view of how early the first expected doc appears. "
        "Higher is better."
    ),
    "average_precision": (
        "Measures average precision of expected doc IDs over the ranked list for this question. "
        "Range: 0–1. "
        "Sensitive to position when multiple expected docs matter. "
        "Higher is better."
    ),
    "avg_average_precision": (
        "Measures mean of per-row average precision for rows with expected doc IDs. "
        "Range: 0–1. "
        "Summarizes ranking quality beyond a single hit. "
        "Higher is better."
    ),
    "answer_f1": (
        "Measures token-level F1 between the generated answer and the gold answer. "
        "Range: 0–1. "
        "Lexical overlap; paraphrases can score low despite being correct. "
        "Higher is better when a gold string exists."
    ),
    "avg_answer_f1": (
        "Measures mean answer F1 across rows with gold answers. "
        "Range: 0–1. "
        "Run-level lexical agreement with references. "
        "Higher is better."
    ),
    "semantic_similarity": (
        "Measures embedding cosine similarity between generated and expected answers. "
        "Range: 0–1. "
        "Higher means more semantically similar; captures paraphrase better than token F1 alone. "
        "Higher is better."
    ),
    "avg_semantic_similarity": (
        "Measures mean semantic similarity across rows with gold answers. "
        "Range: 0–1. "
        "Same embedding cosine definition as per-row semantic_similarity. "
        "Higher is better."
    ),
    "answer_correctness_score": (
        "Measures LLM-evaluated correctness and completeness of the answer relative to the question "
        "and retrieved context. "
        "Range: 0–1 when the judge succeeded. "
        "If `judge_failed` is true, this is None (missing), not a low score. "
        "Depends on judge model and rubric; not a substitute for human review. "
        "Higher is better."
    ),
    "avg_answer_correctness": (
        "Mean of per-row `answer_correctness_score` over **judge-valid** rows only. "
        "Range: 0–1. "
        "Rows with `judge_failed` are excluded from the average. "
        "Higher is better."
    ),
    "ndcg_at_k": (
        "Measures ranking quality: how well relevant documents are ordered in the retrieved list. "
        "Range: 0–1 (normalized discounted cumulative gain). "
        "Rewards placing expected docs higher in the ranking. "
        "Higher is better."
    ),
    "avg_ndcg_at_k": (
        "Measures mean ndcg_at_k across rows with expected doc IDs. "
        "Range: 0–1. "
        "Run-level summary of graded ranking quality. "
        "Higher is better."
    ),
    "groundedness_score": (
        "Measures LLM judge score for how well the answer stays supported by retrieved evidence. "
        "Range: 0–1 when the judge succeeded. "
        "If `judge_failed` is true, None (missing), not zero. "
        "Higher means stronger evidence alignment in the judge’s view. "
        "Higher is better."
    ),
    "avg_groundedness_score": (
        "Measures mean groundedness_score over the run. "
        "Range: 0–1. "
        "Aggregates evidence-grounding as judged. "
        "Higher is better. "
        "Excludes rows where the LLM judge failed (judge_failed)."
    ),
    "citation_faithfulness_score": (
        "Measures LLM judge score for whether [Source N] citations align with the claims they support. "
        "Range: 0–1 when the judge succeeded; None if `judge_failed`. "
        "Focuses on citation–claim consistency, not retrieval recall. "
        "Higher is better."
    ),
    "avg_citation_faithfulness_score": (
        "Measures mean citation_faithfulness_score over the run. "
        "Range: 0–1. "
        "Run-level citation alignment quality. "
        "Higher is better. "
        "Excludes rows where the LLM judge failed (judge_failed)."
    ),
    "answer_relevance_score": (
        "Measures LLM judge score for how well the answer addresses the question. "
        "Range: 0–1 when the judge succeeded; None if `judge_failed`. "
        "Distinct from groundedness (on-topic vs supported-by-context). "
        "Higher is better."
    ),
    "avg_answer_relevance_score": (
        "Measures mean answer_relevance_score over the run. "
        "Range: 0–1. "
        "Run-level on-topic quality from the judge. "
        "Higher is better. "
        "Excludes rows where the LLM judge failed (judge_failed)."
    ),
    "hallucination_score": (
        "Measures LLM judge signal for factual support from context. "
        "Range: 0–1 when the judge succeeded; None if `judge_failed`. "
        "Higher means fewer hallucinations (stronger support from the provided context). "
        "Higher is better."
    ),
    "avg_hallucination_score": (
        "Measures mean hallucination judge signal across rows. "
        "Range: 0–1. "
        "Same direction as per-row hallucination_score: higher implies less hallucination risk. "
        "Higher is better; compare only with the same judge configuration. "
        "Excludes rows where the LLM judge failed (judge_failed)."
    ),
    "hallucination_rate": (
        "Fraction of **judge-valid** rows with `has_hallucination` true. "
        "Range: 0–1 (often shown as a percentage). "
        "Rows with `judge_failed` are excluded from numerator and denominator. "
        "Lower is better."
    ),
    "has_hallucination": (
        "Whether the judge flagged likely hallucination for this row. "
        "Range: boolean when judged; treat as unset (None) if `judge_failed`. "
        "Use together with hallucination_score for context. "
        "False is better."
    ),
    "prompt_doc_id_precision": (
        "Measures precision of prompt-source doc IDs against expected doc IDs. "
        "Range: 0–1. "
        "Share of prompt doc IDs that are in the expected set. "
        "Higher is better."
    ),
    "avg_prompt_doc_id_precision": (
        "Measures mean prompt doc ID precision (prompt sources vs expected). "
        "Range: 0–1. "
        "Run-level context selection precision. "
        "Higher is better."
    ),
    "prompt_doc_id_recall": (
        "Measures recall of expected doc IDs among doc IDs shown in the prompt. "
        "Range: 0–1. "
        "Share of expected docs that made it into the context. "
        "Higher is better."
    ),
    "avg_prompt_doc_id_recall": (
        "Measures mean prompt doc ID recall over the run. "
        "Range: 0–1. "
        "How completely expected docs appear in prompt sources. "
        "Higher is better."
    ),
    "prompt_doc_id_f1": (
        "Measures F1 between prompt-source doc IDs and expected doc IDs. "
        "Range: 0–1. "
        "Balances prompt precision and recall vs expectations. "
        "Higher is better."
    ),
    "avg_prompt_doc_id_f1": (
        "Measures mean prompt doc ID F1 (prompt sources vs expected). "
        "Range: 0–1. "
        "Run-level summary of prompt-side doc alignment. "
        "Higher is better."
    ),
    "citation_doc_id_precision": (
        "Measures precision of doc IDs cited in the answer (via [Source N]) vs expected doc IDs. "
        "Range: 0–1. "
        "Penalizes citations that are not in the gold doc set. "
        "Higher is better."
    ),
    "avg_citation_doc_id_precision": (
        "Measures mean answer-citation doc ID precision. "
        "Range: 0–1. "
        "Run-level citation precision vs expectations. "
        "Higher is better."
    ),
    "citation_doc_id_recall": (
        "Measures recall of expected doc IDs among doc IDs cited in the answer. "
        "Range: 0–1. "
        "Share of expected docs that the answer actually cited. "
        "Higher is better."
    ),
    "avg_citation_doc_id_recall": (
        "Measures mean answer-citation doc ID recall. "
        "Range: 0–1. "
        "Run-level coverage of expected docs in citations. "
        "Higher is better."
    ),
    "citation_doc_id_f1": (
        "Measures F1 between answer-cited doc IDs and expected doc IDs. "
        "Range: 0–1. "
        "Balances citation precision and recall. "
        "Higher is better."
    ),
    "avg_citation_doc_id_f1": (
        "Measures mean answer-citation doc ID F1. "
        "Range: 0–1. "
        "Run-level citation alignment vs gold doc IDs. "
        "Higher is better."
    ),
    "citation_doc_id_overlap_count": (
        "Measures how many expected doc IDs appear among answer citations for this row. "
        "Range: non-negative integer. "
        "Parsed from [Source N] labels mapped to prompt sources. "
        "Higher is better when expecting multiple supporting docs."
    ),
    "citation_doc_ids_count": (
        "Measures how many distinct doc IDs are cited in the answer. "
        "Range: non-negative integer. "
        "From [Source N] references resolved to doc IDs. "
        "Neutral (context); judge quality by overlap and precision/recall, not count alone."
    ),
    "citation_doc_id_hit_rate": (
        "Measures citation hit against expected doc IDs. "
        "Per row: 1 if any expected doc ID is cited ([Source N] mapped to doc IDs), else 0. "
        "Run summary (same key): fraction of rows with expected doc IDs that have such a hit (0–1). "
        "Higher is better."
    ),
    "prompt_doc_id_overlap_count": (
        "Measures how many expected doc IDs appear in prompt sources for this row. "
        "Range: non-negative integer. "
        "Raw overlap count before precision/recall. "
        "Higher is better when more expected docs should appear in context."
    ),
    "retrieved_doc_ids_count": (
        "Measures how many distinct doc IDs retrieval returned for this question. "
        "Range: non-negative integer. "
        "Volume before reranking selection into the prompt. "
        "Neutral (diagnostic); pair with precision and recall."
    ),
    "selected_source_count": (
        "Measures how many distinct sources were selected into the prompt for this run. "
        "Range: non-negative integer. "
        "Depends on chunking and selection policy. "
        "Neutral (diagnostic)."
    ),
    "hit_at_k": (
        "Measures whether any expected doc ID appears in the top-K ranked list. "
        "Per row: 1 if at least one hit, else 0 (0 also when no expected doc IDs). "
        "Run summary: fraction of qualifying rows with a hit (0–1). "
        "Higher is better."
    ),
    "source_hit_rate": (
        "Measures the share of entries where at least one expected source file was retrieved or in prompt. "
        "Range: 0–1. "
        "File-level binary hit rate across the run. "
        "Higher is better."
    ),
    "prompt_doc_id_hit_rate": (
        "Measures prompt-side overlap with expected doc IDs. "
        "Per row: 1 if any expected doc ID appears in prompt sources, else 0. "
        "Run summary: fraction of rows with expected doc IDs that have overlap (0–1). "
        "Higher is better."
    ),
    "retrieval_mode": (
        "Measures which retrieval path ran for this query. "
        "Range: categorical label (e.g. vector vs hybrid). "
        "Use to debug configuration and slice results. "
        "Neutral (context)."
    ),
    "query_rewrite_enabled": (
        "Measures whether query rewrite was enabled for this row’s run. "
        "Range: boolean. "
        "Explains retrieval behavior differences across rows. "
        "Neutral (context); compare runs with the same setting."
    ),
    "hybrid_retrieval_enabled": (
        "Measures whether dense + sparse hybrid retrieval was enabled. "
        "Range: boolean. "
        "Affects recall/precision tradeoffs vs dense-only. "
        "Neutral (context)."
    ),
    "hallucination_flagged_rows": (
        "Measures how many rows in the current filtered slice are flagged as likely hallucinating. "
        "Range: non-negative integer. "
        "Uses the same flag as has_hallucination after filters. "
        "Lower is usually better."
    ),
    "hallucination_flagged_share": (
        "Measures what fraction of rows in the filtered slice are hallucination-flagged. "
        "Range: 0–1 (often shown as a percentage). "
        "Sensitive to table filters and slice size. "
        "Lower is better."
    ),
    "gold_qa_entry_count": (
        "Measures how many gold QA rows are stored for this project. "
        "Range: non-negative integer. "
        "Dataset size available for evaluation. "
        "Neutral (context)."
    ),
    "dataset_entry_count": (
        "Measures how many gold QA rows are used for dataset evaluation on this page. "
        "Range: non-negative integer. "
        "May differ from total stored if filtered. "
        "Neutral (context)."
    ),
    "evaluation_project_context": (
        "Measures which project’s corpus and QA dataset this Evaluation view uses. "
        "Range: project identifier / label. "
        "Ensures metrics are interpreted against the right knowledge base. "
        "Neutral (context)."
    ),
    "table_correctness": (
        "Measures mean answer F1 for rows where the prompt used table context and a gold answer exists. "
        "Range: 0–1. "
        "Conditional slice: only table-context rows with gold. "
        "Higher is better."
    ),
    "image_groundedness": (
        "Measures mean groundedness_score for rows where the prompt used image context. "
        "Range: 0–1. "
        "Conditional slice: image-context rows with a judge groundedness score. "
        "Higher is better."
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
