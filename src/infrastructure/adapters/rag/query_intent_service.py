from __future__ import annotations

from src.domain.query_intent import QueryIntent
from src.domain.retrieval.query_intent_classification import classify_query_intent


class QueryIntentService:
    """
    Heuristic query intent classification for retrieval strategy hints.

    Rules live in :mod:`src.domain.retrieval.query_intent_classification`.
    """

    def classify(self, query: str | None) -> QueryIntent:
        return classify_query_intent(query)
