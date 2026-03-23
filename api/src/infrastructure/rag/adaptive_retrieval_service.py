from __future__ import annotations

from domain.rag.query_intent import QueryIntent
from domain.rag.retrieval.adaptive_retrieval_policy import choose_retrieval_strategy_for_intent
from domain.rag.retrieval_settings import RetrievalSettings
from domain.rag.retrieval_strategy import RetrievalStrategy


class AdaptiveRetrievalService:
    """
    Maps query intent (and light query-shape heuristics) to retrieval parameters.

    Policy lives in :mod:`domain.rag.retrieval.adaptive_retrieval_policy`.
    """

    def choose_strategy(
        self,
        *,
        settings: RetrievalSettings,
        intent: QueryIntent,
        rewritten_query: str,
    ) -> RetrievalStrategy:
        return choose_retrieval_strategy_for_intent(
            settings=settings,
            intent=intent,
            rewritten_query=rewritten_query,
        )
