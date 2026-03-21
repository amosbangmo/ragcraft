"""
Pipeline confidence from reranked retrieval evidence only.

Separate from LLM-judge metrics (groundedness, hallucination, answer relevance).
Computation lives in :mod:`src.domain.retrieval.retrieval_confidence`.
"""

from __future__ import annotations

from src.domain.retrieval.retrieval_confidence import compute_confidence_from_reranked_assets


class ConfidenceService:
    """Combines rerank strength, consistency, and support breadth into [0, 1]."""

    def compute_confidence(
        self,
        *,
        reranked_raw_assets: list[dict],
    ) -> float:
        return compute_confidence_from_reranked_assets(
            reranked_raw_assets=reranked_raw_assets,
        )
