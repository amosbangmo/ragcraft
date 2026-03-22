"""Deterministic ranking and set-overlap metrics for retrieval evaluation."""

from __future__ import annotations

import math


class RetrievalMetricsService:
    """Pure metric formulas over ranked doc id lists and gold sets."""

    def compute_ndcg_at_k(
        self,
        *,
        ranked_doc_ids: list[str],
        expected_doc_ids: set[str],
    ) -> float:
        """
        NDCG over the full ranked list (K = len(ranked_doc_ids)).
        Binary relevance: 1 if doc_id is in expected_doc_ids, else 0.
        DCG uses sum(rel / log2(rank + 1)) for 1-based rank.
        """
        if not ranked_doc_ids or not expected_doc_ids:
            return 0.0

        def _dcg(relevances: list[float]) -> float:
            total = 0.0
            for i, rel in enumerate(relevances):
                rank = i + 1
                total += rel / math.log2(rank + 1)
            return total

        rel = [1.0 if doc_id in expected_doc_ids else 0.0 for doc_id in ranked_doc_ids]
        dcg_score = _dcg(rel)
        ideal = sorted(rel, reverse=True)
        idcg = _dcg(ideal)
        if idcg <= 0.0:
            return 0.0
        return dcg_score / idcg

    def compute_precision_at_k(
        self,
        *,
        ranked_doc_ids: list[str],
        expected_doc_ids: set[str],
    ) -> float:
        if not ranked_doc_ids:
            return 0.0

        relevant_retrieved = sum(1 for doc_id in ranked_doc_ids if doc_id in expected_doc_ids)
        return relevant_retrieved / len(ranked_doc_ids)

    def compute_reciprocal_rank(
        self,
        *,
        ranked_doc_ids: list[str],
        expected_doc_ids: set[str],
    ) -> float:
        for index, doc_id in enumerate(ranked_doc_ids, start=1):
            if doc_id in expected_doc_ids:
                return 1.0 / index
        return 0.0

    def compute_average_precision(
        self,
        *,
        ranked_doc_ids: list[str],
        expected_doc_ids: set[str],
    ) -> float:
        if not ranked_doc_ids or not expected_doc_ids:
            return 0.0

        precision_sum = 0.0
        relevant_found = 0

        for index, doc_id in enumerate(ranked_doc_ids, start=1):
            if doc_id not in expected_doc_ids:
                continue

            relevant_found += 1
            precision_at_index = relevant_found / index
            precision_sum += precision_at_index

        if relevant_found == 0:
            return 0.0

        return precision_sum / len(expected_doc_ids)

    def compute_set_precision_recall_f1(
        self,
        *,
        predicted_values: set[str],
        expected_values: set[str],
    ) -> tuple[float, float, float]:
        if not expected_values:
            return 0.0, 0.0, 0.0

        if not predicted_values:
            return 0.0, 0.0, 0.0

        overlap = len(predicted_values.intersection(expected_values))

        precision = overlap / len(predicted_values) if predicted_values else 0.0
        recall = overlap / len(expected_values) if expected_values else 0.0

        if precision + recall == 0:
            f1 = 0.0
        else:
            f1 = 2 * precision * recall / (precision + recall)

        return precision, recall, f1
