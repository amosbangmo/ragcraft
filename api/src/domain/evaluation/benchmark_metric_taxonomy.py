"""
Structured taxonomy for benchmark / dataset evaluation metrics.

This module is the **single source of truth** for:

- **Families** — what part of the RAG stack a metric belongs to
- **Direction** — whether higher or lower values are better (for comparisons)
- **Scoring kind** — deterministic overlap, LLM judge, pipeline instrumentation, etc.
- **Judge-failed handling** — how rows with ``judge_failed`` interact with the metric

Human-readable tooltips live in :mod:`src.ui.metric_help` (``METRIC_HELP``).
Dashboard section order is documented in :func:`src.ui.evaluation_dashboard.render_evaluation_dashboard`.

Row keys included in Pearson correlation are listed in ``CORRELATION_METRIC_KEYS``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final


class BenchmarkMetricFamily(str, Enum):
    """Coarse grouping used in docs, exports, and mental models (not a wire format)."""

    RETRIEVAL_RANKED_DOCS = "retrieval_ranked_docs"
    RETRIEVAL_SOURCES = "retrieval_sources"
    PROMPT_DOC_OVERLAP = "prompt_doc_overlap"
    ANSWER_CITATION_OVERLAP = "answer_citation_overlap"
    GOLD_ANSWER_OVERLAP = "gold_answer_overlap"
    LLM_JUDGE = "llm_judge"
    PIPELINE_RUNTIME = "pipeline_runtime"
    MULTIMODAL = "multimodal"
    DATASET_OR_UI_CONTEXT = "dataset_or_ui_context"


class MetricDirection(str, Enum):
    HIGHER_BETTER = "higher_better"
    LOWER_BETTER = "lower_better"
    NEUTRAL = "neutral"


class MetricScoringKind(str, Enum):
    """How the metric is produced."""

    DETERMINISTIC = "deterministic"
    EMBEDDING = "embedding"
    LLM_JUDGE = "llm_judge"
    PIPELINE = "pipeline"
    CONFIG_CONTEXT = "config_context"
    UI_SLICE = "ui_slice"
    RUN_METADATA = "run_metadata"


class JudgeFailedPolicy(str, Enum):
    """
    Whether ``judge_failed`` affects the metric.

    ``ROW_FIELDS_MISSING`` — per-row judge fields are absent (not zero) when the judge failed.
    ``EXCLUDED_FROM_JUDGE_AGGREGATES`` — run-level ``avg_*`` judge means and ``hallucination_rate``
    exclude judge-failed rows (see :class:`~domain.benchmark_result.BenchmarkSummary`).
    ``NOT_APPLICABLE`` — judge outcome does not define this metric.
    """

    NOT_APPLICABLE = "not_applicable"
    ROW_FIELDS_MISSING = "row_fields_missing"
    EXCLUDED_FROM_JUDGE_AGGREGATES = "excluded_from_judge_aggregates"


@dataclass(frozen=True)
class BenchmarkMetricSpec:
    family: BenchmarkMetricFamily
    direction: MetricDirection
    scoring_kind: MetricScoringKind
    judge_failed_policy: JudgeFailedPolicy


def _spec(
    family: BenchmarkMetricFamily,
    direction: MetricDirection,
    scoring: MetricScoringKind,
    judge: JudgeFailedPolicy,
) -> BenchmarkMetricSpec:
    return BenchmarkMetricSpec(
        family=family,
        direction=direction,
        scoring_kind=scoring,
        judge_failed_policy=judge,
    )


def _bulk(
    keys: tuple[str, ...],
    family: BenchmarkMetricFamily,
    direction: MetricDirection,
    scoring: MetricScoringKind,
    judge: JudgeFailedPolicy,
) -> dict[str, BenchmarkMetricSpec]:
    s = _spec(family, direction, scoring, judge)
    return {k: s for k in keys}


# Keys must stay stable: UI, exports, and sessions rely on these strings.
METRIC_SPECS: dict[str, BenchmarkMetricSpec] = {}
METRIC_SPECS.update(
    _bulk(
        (
            "recall_at_k",
            "avg_recall_at_k",
            "precision_at_k",
            "avg_precision_at_k",
            "reciprocal_rank",
            "avg_reciprocal_rank",
            "average_precision",
            "avg_average_precision",
            "ndcg_at_k",
            "avg_ndcg_at_k",
            "hit_at_k",
            "retrieved_doc_ids_count",
        ),
        BenchmarkMetricFamily.RETRIEVAL_RANKED_DOCS,
        MetricDirection.HIGHER_BETTER,
        MetricScoringKind.DETERMINISTIC,
        JudgeFailedPolicy.NOT_APPLICABLE,
    )
)
METRIC_SPECS.update(
    _bulk(
        ("source_recall", "avg_source_recall", "source_hit_rate"),
        BenchmarkMetricFamily.RETRIEVAL_SOURCES,
        MetricDirection.HIGHER_BETTER,
        MetricScoringKind.DETERMINISTIC,
        JudgeFailedPolicy.NOT_APPLICABLE,
    )
)
METRIC_SPECS.update(
    _bulk(
        (
            "prompt_doc_id_precision",
            "avg_prompt_doc_id_precision",
            "prompt_doc_id_recall",
            "avg_prompt_doc_id_recall",
            "prompt_doc_id_f1",
            "avg_prompt_doc_id_f1",
            "prompt_doc_id_hit_rate",
            "prompt_doc_id_overlap_count",
        ),
        BenchmarkMetricFamily.PROMPT_DOC_OVERLAP,
        MetricDirection.HIGHER_BETTER,
        MetricScoringKind.DETERMINISTIC,
        JudgeFailedPolicy.NOT_APPLICABLE,
    )
)
METRIC_SPECS.update(
    _bulk(
        (
            "citation_doc_id_precision",
            "avg_citation_doc_id_precision",
            "citation_doc_id_recall",
            "avg_citation_doc_id_recall",
            "citation_doc_id_f1",
            "avg_citation_doc_id_f1",
            "citation_doc_id_hit_rate",
            "citation_doc_id_overlap_count",
            "citation_doc_ids_count",
        ),
        BenchmarkMetricFamily.ANSWER_CITATION_OVERLAP,
        MetricDirection.HIGHER_BETTER,
        MetricScoringKind.DETERMINISTIC,
        JudgeFailedPolicy.NOT_APPLICABLE,
    )
)
METRIC_SPECS.update(
    _bulk(
        ("answer_f1", "avg_answer_f1", "table_correctness"),
        BenchmarkMetricFamily.GOLD_ANSWER_OVERLAP,
        MetricDirection.HIGHER_BETTER,
        MetricScoringKind.DETERMINISTIC,
        JudgeFailedPolicy.NOT_APPLICABLE,
    )
)
METRIC_SPECS["semantic_similarity"] = _spec(
    BenchmarkMetricFamily.GOLD_ANSWER_OVERLAP,
    MetricDirection.HIGHER_BETTER,
    MetricScoringKind.EMBEDDING,
    JudgeFailedPolicy.NOT_APPLICABLE,
)
METRIC_SPECS["avg_semantic_similarity"] = _spec(
    BenchmarkMetricFamily.GOLD_ANSWER_OVERLAP,
    MetricDirection.HIGHER_BETTER,
    MetricScoringKind.EMBEDDING,
    JudgeFailedPolicy.NOT_APPLICABLE,
)

METRIC_SPECS.update(
    {
        "groundedness_score": _spec(
            BenchmarkMetricFamily.LLM_JUDGE,
            MetricDirection.HIGHER_BETTER,
            MetricScoringKind.LLM_JUDGE,
            JudgeFailedPolicy.ROW_FIELDS_MISSING,
        ),
        "avg_groundedness_score": _spec(
            BenchmarkMetricFamily.LLM_JUDGE,
            MetricDirection.HIGHER_BETTER,
            MetricScoringKind.LLM_JUDGE,
            JudgeFailedPolicy.EXCLUDED_FROM_JUDGE_AGGREGATES,
        ),
        "citation_faithfulness_score": _spec(
            BenchmarkMetricFamily.LLM_JUDGE,
            MetricDirection.HIGHER_BETTER,
            MetricScoringKind.LLM_JUDGE,
            JudgeFailedPolicy.ROW_FIELDS_MISSING,
        ),
        "avg_citation_faithfulness_score": _spec(
            BenchmarkMetricFamily.LLM_JUDGE,
            MetricDirection.HIGHER_BETTER,
            MetricScoringKind.LLM_JUDGE,
            JudgeFailedPolicy.EXCLUDED_FROM_JUDGE_AGGREGATES,
        ),
        "answer_relevance_score": _spec(
            BenchmarkMetricFamily.LLM_JUDGE,
            MetricDirection.HIGHER_BETTER,
            MetricScoringKind.LLM_JUDGE,
            JudgeFailedPolicy.ROW_FIELDS_MISSING,
        ),
        "avg_answer_relevance_score": _spec(
            BenchmarkMetricFamily.LLM_JUDGE,
            MetricDirection.HIGHER_BETTER,
            MetricScoringKind.LLM_JUDGE,
            JudgeFailedPolicy.EXCLUDED_FROM_JUDGE_AGGREGATES,
        ),
        "answer_correctness_score": _spec(
            BenchmarkMetricFamily.LLM_JUDGE,
            MetricDirection.HIGHER_BETTER,
            MetricScoringKind.LLM_JUDGE,
            JudgeFailedPolicy.ROW_FIELDS_MISSING,
        ),
        "avg_answer_correctness": _spec(
            BenchmarkMetricFamily.LLM_JUDGE,
            MetricDirection.HIGHER_BETTER,
            MetricScoringKind.LLM_JUDGE,
            JudgeFailedPolicy.EXCLUDED_FROM_JUDGE_AGGREGATES,
        ),
        "hallucination_score": _spec(
            BenchmarkMetricFamily.LLM_JUDGE,
            MetricDirection.HIGHER_BETTER,
            MetricScoringKind.LLM_JUDGE,
            JudgeFailedPolicy.ROW_FIELDS_MISSING,
        ),
        "avg_hallucination_score": _spec(
            BenchmarkMetricFamily.LLM_JUDGE,
            MetricDirection.HIGHER_BETTER,
            MetricScoringKind.LLM_JUDGE,
            JudgeFailedPolicy.EXCLUDED_FROM_JUDGE_AGGREGATES,
        ),
        "has_hallucination": _spec(
            BenchmarkMetricFamily.LLM_JUDGE,
            MetricDirection.NEUTRAL,
            MetricScoringKind.LLM_JUDGE,
            JudgeFailedPolicy.ROW_FIELDS_MISSING,
        ),
        "hallucination_rate": _spec(
            BenchmarkMetricFamily.LLM_JUDGE,
            MetricDirection.LOWER_BETTER,
            MetricScoringKind.LLM_JUDGE,
            JudgeFailedPolicy.EXCLUDED_FROM_JUDGE_AGGREGATES,
        ),
        "judge_failed": _spec(
            BenchmarkMetricFamily.LLM_JUDGE,
            MetricDirection.NEUTRAL,
            MetricScoringKind.LLM_JUDGE,
            JudgeFailedPolicy.NOT_APPLICABLE,
        ),
        "judge_failure_reason": _spec(
            BenchmarkMetricFamily.LLM_JUDGE,
            MetricDirection.NEUTRAL,
            MetricScoringKind.LLM_JUDGE,
            JudgeFailedPolicy.NOT_APPLICABLE,
        ),
    }
)

METRIC_SPECS.update(
    _bulk(
        ("latency_ms", "avg_latency_ms"),
        BenchmarkMetricFamily.PIPELINE_RUNTIME,
        MetricDirection.LOWER_BETTER,
        MetricScoringKind.PIPELINE,
        JudgeFailedPolicy.NOT_APPLICABLE,
    )
)
METRIC_SPECS.update(
    _bulk(
        ("confidence", "avg_confidence"),
        BenchmarkMetricFamily.PIPELINE_RUNTIME,
        MetricDirection.HIGHER_BETTER,
        MetricScoringKind.PIPELINE,
        JudgeFailedPolicy.NOT_APPLICABLE,
    )
)
METRIC_SPECS["pipeline_failure_rate"] = _spec(
    BenchmarkMetricFamily.PIPELINE_RUNTIME,
    MetricDirection.LOWER_BETTER,
    MetricScoringKind.PIPELINE,
    JudgeFailedPolicy.NOT_APPLICABLE,
)
METRIC_SPECS.update(
    _bulk(
        (
            "query_rewrite_ms",
            "retrieval_ms",
            "reranking_ms",
            "prompt_build_ms",
            "answer_generation_ms",
        ),
        BenchmarkMetricFamily.PIPELINE_RUNTIME,
        MetricDirection.LOWER_BETTER,
        MetricScoringKind.PIPELINE,
        JudgeFailedPolicy.NOT_APPLICABLE,
    )
)

METRIC_SPECS.update(
    _bulk(
        (
            "table_usage_rate",
            "image_usage_rate",
            "multimodal_answers_rate",
        ),
        BenchmarkMetricFamily.MULTIMODAL,
        MetricDirection.NEUTRAL,
        MetricScoringKind.DETERMINISTIC,
        JudgeFailedPolicy.NOT_APPLICABLE,
    )
)
METRIC_SPECS["image_groundedness"] = _spec(
    BenchmarkMetricFamily.MULTIMODAL,
    MetricDirection.HIGHER_BETTER,
    MetricScoringKind.LLM_JUDGE,
    JudgeFailedPolicy.EXCLUDED_FROM_JUDGE_AGGREGATES,
)
METRIC_SPECS["eligible_rows"] = _spec(
    BenchmarkMetricFamily.MULTIMODAL,
    MetricDirection.NEUTRAL,
    MetricScoringKind.RUN_METADATA,
    JudgeFailedPolicy.NOT_APPLICABLE,
)

METRIC_SPECS.update(
    _bulk(
        (
            "retrieval_mode",
            "query_rewrite_enabled",
            "hybrid_retrieval_enabled",
            "selected_source_count",
        ),
        BenchmarkMetricFamily.DATASET_OR_UI_CONTEXT,
        MetricDirection.NEUTRAL,
        MetricScoringKind.CONFIG_CONTEXT,
        JudgeFailedPolicy.NOT_APPLICABLE,
    )
)
METRIC_SPECS.update(
    _bulk(
        (
            "gold_qa_entry_count",
            "dataset_entry_count",
            "evaluation_project_context",
        ),
        BenchmarkMetricFamily.DATASET_OR_UI_CONTEXT,
        MetricDirection.NEUTRAL,
        MetricScoringKind.RUN_METADATA,
        JudgeFailedPolicy.NOT_APPLICABLE,
    )
)
METRIC_SPECS.update(
    _bulk(
        ("hallucination_flagged_rows", "hallucination_flagged_share"),
        BenchmarkMetricFamily.DATASET_OR_UI_CONTEXT,
        MetricDirection.LOWER_BETTER,
        MetricScoringKind.UI_SLICE,
        JudgeFailedPolicy.NOT_APPLICABLE,
    )
)

# Summary-only / row bookkeeping (evaluation_service summary_payload and row payloads)
METRIC_SPECS.update(
    {
        "total_entries": _spec(
            BenchmarkMetricFamily.DATASET_OR_UI_CONTEXT,
            MetricDirection.NEUTRAL,
            MetricScoringKind.RUN_METADATA,
            JudgeFailedPolicy.NOT_APPLICABLE,
        ),
        "successful_queries": _spec(
            BenchmarkMetricFamily.PIPELINE_RUNTIME,
            MetricDirection.NEUTRAL,
            MetricScoringKind.RUN_METADATA,
            JudgeFailedPolicy.NOT_APPLICABLE,
        ),
        "entries_with_expected_doc_ids": _spec(
            BenchmarkMetricFamily.DATASET_OR_UI_CONTEXT,
            MetricDirection.NEUTRAL,
            MetricScoringKind.RUN_METADATA,
            JudgeFailedPolicy.NOT_APPLICABLE,
        ),
        "entries_with_expected_sources": _spec(
            BenchmarkMetricFamily.DATASET_OR_UI_CONTEXT,
            MetricDirection.NEUTRAL,
            MetricScoringKind.RUN_METADATA,
            JudgeFailedPolicy.NOT_APPLICABLE,
        ),
        "entries_with_expected_answers": _spec(
            BenchmarkMetricFamily.DATASET_OR_UI_CONTEXT,
            MetricDirection.NEUTRAL,
            MetricScoringKind.RUN_METADATA,
            JudgeFailedPolicy.NOT_APPLICABLE,
        ),
        "doc_id_overlap_count": _spec(
            BenchmarkMetricFamily.RETRIEVAL_RANKED_DOCS,
            MetricDirection.HIGHER_BETTER,
            MetricScoringKind.DETERMINISTIC,
            JudgeFailedPolicy.NOT_APPLICABLE,
        ),
        "expected_doc_ids_count": _spec(
            BenchmarkMetricFamily.DATASET_OR_UI_CONTEXT,
            MetricDirection.NEUTRAL,
            MetricScoringKind.RUN_METADATA,
            JudgeFailedPolicy.NOT_APPLICABLE,
        ),
        "expected_sources_count": _spec(
            BenchmarkMetricFamily.DATASET_OR_UI_CONTEXT,
            MetricDirection.NEUTRAL,
            MetricScoringKind.RUN_METADATA,
            JudgeFailedPolicy.NOT_APPLICABLE,
        ),
        "retrieved_sources_count": _spec(
            BenchmarkMetricFamily.RETRIEVAL_SOURCES,
            MetricDirection.NEUTRAL,
            MetricScoringKind.DETERMINISTIC,
            JudgeFailedPolicy.NOT_APPLICABLE,
        ),
        "source_overlap_count": _spec(
            BenchmarkMetricFamily.RETRIEVAL_SOURCES,
            MetricDirection.HIGHER_BETTER,
            MetricScoringKind.DETERMINISTIC,
            JudgeFailedPolicy.NOT_APPLICABLE,
        ),
        "has_expected_answer": _spec(
            BenchmarkMetricFamily.DATASET_OR_UI_CONTEXT,
            MetricDirection.NEUTRAL,
            MetricScoringKind.RUN_METADATA,
            JudgeFailedPolicy.NOT_APPLICABLE,
        ),
        "pipeline_failed": _spec(
            BenchmarkMetricFamily.PIPELINE_RUNTIME,
            MetricDirection.NEUTRAL,
            MetricScoringKind.PIPELINE,
            JudgeFailedPolicy.NOT_APPLICABLE,
        ),
    }
)


FAMILY_GUIDE: dict[BenchmarkMetricFamily, str] = {
    BenchmarkMetricFamily.RETRIEVAL_RANKED_DOCS: (
        "Retrieval quality over ranked chunk/doc IDs vs gold ``expected_doc_ids`` "
        "(recall, precision, MRR, AP, NDCG, hit rates)."
    ),
    BenchmarkMetricFamily.RETRIEVAL_SOURCES: (
        "File- or source-path coverage vs gold ``expected_sources`` in retrieval or prompt context."
    ),
    BenchmarkMetricFamily.PROMPT_DOC_OVERLAP: (
        "How well doc IDs actually placed in the LLM prompt match gold ``expected_doc_ids``."
    ),
    BenchmarkMetricFamily.ANSWER_CITATION_OVERLAP: (
        "How well ``[Source N]`` citations in the answer resolve to doc IDs vs gold ``expected_doc_ids``."
    ),
    BenchmarkMetricFamily.GOLD_ANSWER_OVERLAP: (
        "Lexical and embedding similarity between the generated answer and gold text (when present)."
    ),
    BenchmarkMetricFamily.LLM_JUDGE: (
        "Model-graded rubric scores and flags; per-row fields are missing (not zero) when ``judge_failed``."
    ),
    BenchmarkMetricFamily.PIPELINE_RUNTIME: (
        "Latency, confidence, and pipeline success vs failure (orthogonal to judge outages)."
    ),
    BenchmarkMetricFamily.MULTIMODAL: (
        "Usage of tables/images in context and conditional quality slices over those rows."
    ),
    BenchmarkMetricFamily.DATASET_OR_UI_CONTEXT: (
        "Dataset sizing, UI-only slices, and configuration labels that explain a run."
    ),
}


# Display label → row payload key (``BenchmarkRow.data`` / ``to_dict``).
CORRELATION_METRIC_KEYS: tuple[tuple[str, str], ...] = (
    ("confidence", "confidence"),
    ("answer_f1", "answer_f1"),
    ("recall_at_k", "recall_at_k"),
    ("reciprocal_rank", "reciprocal_rank"),
    ("average_precision", "average_precision"),
    ("groundedness_score", "groundedness_score"),
    ("citation_faithfulness_score", "citation_faithfulness_score"),
    ("answer_relevance_score", "answer_relevance_score"),
    ("answer_correctness_score", "answer_correctness_score"),
    ("semantic_similarity", "semantic_similarity"),
    ("ndcg_at_k", "ndcg_at_k"),
    ("prompt_doc_id_precision", "prompt_doc_id_precision"),
    ("prompt_doc_id_recall", "prompt_doc_id_recall"),
    ("citation_doc_id_f1", "citation_doc_id_f1"),
    ("latency_ms", "latency_ms"),
)


LOWER_IS_BETTER_METRIC_KEYS: Final[frozenset[str]] = frozenset(
    k for k, spec in METRIC_SPECS.items() if spec.direction == MetricDirection.LOWER_BETTER
)

CRITICAL_REGRESSION_METRIC_KEYS: Final[frozenset[str]] = frozenset(
    {"avg_answer_f1", "avg_groundedness_score", "avg_answer_correctness"}
)


def metric_spec(metric_key: str) -> BenchmarkMetricSpec | None:
    """Return taxonomy metadata for a metric key, or ``None`` if unknown."""
    return METRIC_SPECS.get(metric_key)


def is_lower_better(metric_key: str) -> bool:
    """Whether a larger numeric value is worse (used by benchmark A vs B deltas)."""
    spec = METRIC_SPECS.get(metric_key)
    if spec is None:
        return False
    return spec.direction == MetricDirection.LOWER_BETTER


def markdown_family_guide_lines() -> list[str]:
    """Indented bullet lines documenting each :class:`BenchmarkMetricFamily` for Markdown exports."""
    lines: list[str] = ["- **Metric families** (see ``src/domain/benchmark_metric_taxonomy.py``):"]
    for fam in BenchmarkMetricFamily:
        lines.append(f"  - `{fam.value}`: {FAMILY_GUIDE[fam]}")
    lines.append(
        "- **A vs B comparison:** Deltas are **B − A**. Metrics in "
        "``LOWER_IS_BETTER_METRIC_KEYS`` improve when the delta is **negative**."
    )
    return lines
