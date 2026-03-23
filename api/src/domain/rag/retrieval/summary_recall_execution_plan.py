"""Pure policy: how summary recall chooses k, hybrid, and adaptive vs fixed overrides."""

from __future__ import annotations

from domain.rag.query_intent import QueryIntent
from domain.rag.retrieval.adaptive_retrieval_policy import choose_retrieval_strategy_for_intent
from domain.rag.retrieval_settings import RetrievalSettings
from domain.rag.retrieval_strategy import RetrievalStrategy


def resolve_summary_recall_execution_plan(
    *,
    settings: RetrievalSettings,
    intent: QueryIntent,
    rewritten_query: str,
    enable_hybrid_retrieval_override: bool | None,
) -> tuple[RetrievalStrategy, bool, int, bool]:
    """
    Returns ``(strategy, enable_hybrid_retrieval, similarity_search_k, use_adaptive_retrieval)``.

    When ``enable_hybrid_retrieval_override`` is ``None``, adaptive intent-based strategy is used.
    When set, project/settings toggles fix hybrid and k (no intent-based adaptation).
    """
    use_adaptive_retrieval = enable_hybrid_retrieval_override is None
    if use_adaptive_retrieval:
        strategy = choose_retrieval_strategy_for_intent(
            settings=settings,
            intent=intent,
            rewritten_query=rewritten_query,
        )
        return strategy, strategy.use_hybrid, strategy.k, True

    strategy = RetrievalStrategy(
        k=max(1, int(settings.similarity_search_k)),
        use_hybrid=bool(settings.enable_hybrid_retrieval),
        apply_filters=True,
    )
    return strategy, settings.enable_hybrid_retrieval, strategy.k, False
