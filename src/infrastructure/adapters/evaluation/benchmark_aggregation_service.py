"""Aggregate per-row benchmark lists into the summary payload (deterministic)."""

from __future__ import annotations

from src.domain.evaluation.benchmark_accumulator import BenchmarkAccumulator
from src.domain.evaluation.benchmark_math import mean_round, rate


class BenchmarkAggregationService:
    def build_summary_payload(self, acc: BenchmarkAccumulator) -> dict:
        rows = acc.rows
        hallucination_flags = acc.hallucination_flags

        summary_payload = {
            "total_entries": len(rows),
            "successful_queries": acc.successful_queries,
            "entries_with_expected_doc_ids": acc.entries_with_expected_doc_ids,
            "entries_with_expected_sources": acc.entries_with_expected_sources,
            "entries_with_expected_answers": acc.entries_with_expected_answers,
            "avg_recall_at_k": mean_round(acc.recall_at_k_values, 2),
            "avg_source_recall": mean_round(acc.source_recall_values, 2),
            "avg_precision_at_k": mean_round(acc.precision_at_k_values, 2),
            "avg_reciprocal_rank": mean_round(acc.reciprocal_rank_values, 2),
            "avg_average_precision": mean_round(acc.average_precision_values, 2),
            "avg_ndcg_at_k": mean_round(acc.ndcg_at_k_values, 2),
            "avg_confidence": mean_round(acc.confidence_values, 2),
            "avg_latency_ms": mean_round(acc.latency_values, 1),
            "pipeline_failure_rate": rate(len(rows) - acc.successful_queries, len(rows)),
            "hit_at_k": rate(acc.doc_id_hits, acc.entries_with_expected_doc_ids),
            "source_hit_rate": rate(acc.source_hits, acc.entries_with_expected_sources),
            "avg_answer_f1": mean_round(acc.answer_f1_values, 2),
            "avg_semantic_similarity": mean_round(acc.semantic_similarity_values, 2),
            "avg_prompt_doc_id_precision": mean_round(acc.prompt_doc_id_precision_values, 2),
            "avg_prompt_doc_id_recall": mean_round(acc.prompt_doc_id_recall_values, 2),
            "avg_prompt_doc_id_f1": mean_round(acc.prompt_doc_id_f1_values, 2),
            "prompt_doc_id_hit_rate": rate(acc.prompt_doc_id_hits, acc.entries_with_expected_doc_ids),
            "avg_citation_doc_id_precision": mean_round(acc.citation_doc_id_precision_values, 2),
            "avg_citation_doc_id_recall": mean_round(acc.citation_doc_id_recall_values, 2),
            "avg_citation_doc_id_f1": mean_round(acc.citation_doc_id_f1_values, 2),
            "citation_doc_id_hit_rate": rate(
                acc.citation_doc_id_hits,
                acc.entries_with_expected_doc_ids,
            ),
            "avg_groundedness_score": mean_round(acc.groundedness_values, 2),
            "avg_citation_faithfulness_score": mean_round(acc.citation_faithfulness_values, 2),
            "avg_answer_relevance_score": mean_round(acc.answer_relevance_values, 2),
            "avg_answer_correctness": mean_round(acc.answer_correctness_values, 2),
            "avg_hallucination_score": mean_round(acc.hallucination_score_values, 2),
            "hallucination_rate": (
                round(
                    sum(1 for flag in hallucination_flags if flag) / len(hallucination_flags),
                    2,
                )
                if hallucination_flags
                else None
            ),
        }
        return summary_payload
