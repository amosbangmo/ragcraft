"""Mutable accumulator for gold QA benchmark runs (shared by row processing and summary build)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BenchmarkAccumulator:
    """Mutable counters and value lists collected while evaluating each gold QA row."""

    rows: list = field(default_factory=list)

    recall_at_k_values: list[float] = field(default_factory=list)
    source_recall_values: list[float] = field(default_factory=list)
    precision_at_k_values: list[float] = field(default_factory=list)
    reciprocal_rank_values: list[float] = field(default_factory=list)
    average_precision_values: list[float] = field(default_factory=list)
    confidence_values: list[float] = field(default_factory=list)
    latency_values: list[float] = field(default_factory=list)

    answer_f1_values: list[float] = field(default_factory=list)

    prompt_doc_id_precision_values: list[float] = field(default_factory=list)
    prompt_doc_id_recall_values: list[float] = field(default_factory=list)
    prompt_doc_id_f1_values: list[float] = field(default_factory=list)

    citation_doc_id_precision_values: list[float] = field(default_factory=list)
    citation_doc_id_recall_values: list[float] = field(default_factory=list)
    citation_doc_id_f1_values: list[float] = field(default_factory=list)

    groundedness_values: list[float] = field(default_factory=list)
    citation_faithfulness_values: list[float] = field(default_factory=list)
    answer_relevance_values: list[float] = field(default_factory=list)
    hallucination_score_values: list[float] = field(default_factory=list)
    hallucination_flags: list[bool] = field(default_factory=list)
    answer_correctness_values: list[float] = field(default_factory=list)
    semantic_similarity_values: list[float] = field(default_factory=list)
    ndcg_at_k_values: list[float] = field(default_factory=list)

    entries_with_expected_doc_ids: int = 0
    entries_with_expected_sources: int = 0
    entries_with_expected_answers: int = 0

    doc_id_hits: int = 0
    source_hits: int = 0
    prompt_doc_id_hits: int = 0
    citation_doc_id_hits: int = 0
    successful_queries: int = 0
