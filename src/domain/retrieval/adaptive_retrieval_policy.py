"""Map query intent and query shape to retrieval strategy parameters (pure rules)."""

from __future__ import annotations

from src.domain.query_intent import QueryIntent
from src.domain.retrieval_settings import RetrievalSettings
from src.domain.retrieval_strategy import RetrievalStrategy


def choose_retrieval_strategy_for_intent(
    *,
    settings: RetrievalSettings,
    intent: QueryIntent,
    rewritten_query: str,
) -> RetrievalStrategy:
    """
    Baseline values come from retrieval settings; UNKNOWN intent preserves that baseline.
    """
    baseline_k = max(1, int(settings.similarity_search_k))
    baseline_hybrid = bool(settings.enable_hybrid_retrieval)

    words = (rewritten_query or "").split()
    n_words = len(words)
    long_query = n_words > 28
    short_query = n_words < 6

    if intent is QueryIntent.UNKNOWN:
        return RetrievalStrategy(
            k=baseline_k,
            use_hybrid=baseline_hybrid,
            apply_filters=True,
        )

    if intent is QueryIntent.FACTUAL:
        k = 5 if long_query else 4
        if short_query:
            k = max(3, k - 1)
        return RetrievalStrategy(
            k=max(1, min(k, baseline_k)),
            use_hybrid=False,
            apply_filters=False,
        )

    if intent is QueryIntent.EXPLORATORY:
        k = 12 if long_query else (8 if short_query else 10)
        return RetrievalStrategy(
            k=max(1, min(k, baseline_k * 2)),
            use_hybrid=True,
            apply_filters=True,
        )

    if intent in (QueryIntent.TABLE, QueryIntent.IMAGE):
        k = 10 if long_query else 8
        return RetrievalStrategy(
            k=max(1, min(k, baseline_k * 2)),
            use_hybrid=True,
            apply_filters=True,
        )

    if intent is QueryIntent.COMPARISON:
        k = 8 if long_query else 7
        return RetrievalStrategy(
            k=max(1, min(k, baseline_k * 2)),
            use_hybrid=True,
            apply_filters=True,
        )

    return RetrievalStrategy(
        k=baseline_k,
        use_hybrid=baseline_hybrid,
        apply_filters=True,
    )
