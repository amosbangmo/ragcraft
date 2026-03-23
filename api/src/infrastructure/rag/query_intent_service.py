from __future__ import annotations

from domain.rag.query_intent import QueryIntent
from domain.rag.retrieval.query_intent_classification import classify_query_intent


class QueryIntentService:
    """
    Heuristic query intent classification for retrieval strategy hints.

    Rules live in :mod:`domain.rag.retrieval.query_intent_classification`.
    """

    def classify(self, query: str | None) -> QueryIntent:
        return classify_query_intent(query)
