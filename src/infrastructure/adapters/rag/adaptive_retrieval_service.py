from __future__ import annotations

from src.domain.query_intent import QueryIntent
from src.domain.retrieval.adaptive_retrieval_policy import choose_retrieval_strategy_for_intent
from src.domain.retrieval_settings import RetrievalSettings
from src.domain.retrieval_strategy import RetrievalStrategy


class AdaptiveRetrievalService:
    """
    Maps query intent (and light query-shape heuristics) to retrieval parameters.

    Policy lives in :mod:`src.domain.retrieval.adaptive_retrieval_policy`.
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
