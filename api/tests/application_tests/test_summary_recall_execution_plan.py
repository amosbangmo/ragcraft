from __future__ import annotations

from dataclasses import replace

from infrastructure.config.config import RETRIEVAL_CONFIG
from domain.rag.query_intent import QueryIntent
from domain.rag.retrieval.summary_recall_execution_plan import resolve_summary_recall_execution_plan
from domain.rag.retrieval_settings import RetrievalSettings


def _settings() -> RetrievalSettings:
    return RetrievalSettings.from_object(RETRIEVAL_CONFIG)


def test_none_override_uses_adaptive_strategy() -> None:
    settings = replace(_settings(), similarity_search_k=15, enable_hybrid_retrieval=True)
    strategy, hybrid, k, adaptive = resolve_summary_recall_execution_plan(
        settings=settings,
        intent=QueryIntent.FACTUAL,
        rewritten_query="short",
        enable_hybrid_retrieval_override=None,
    )
    assert adaptive is True
    assert hybrid == strategy.use_hybrid
    assert k == strategy.k


def test_explicit_override_disables_adaptive_uses_settings_hybrid() -> None:
    settings = replace(_settings(), similarity_search_k=12, enable_hybrid_retrieval=False)
    strategy, hybrid, k, adaptive = resolve_summary_recall_execution_plan(
        settings=settings,
        intent=QueryIntent.EXPLORATORY,
        rewritten_query="ignored for k when not adaptive",
        enable_hybrid_retrieval_override=False,
    )
    assert adaptive is False
    assert hybrid is False
    assert k == 12
    assert strategy.use_hybrid is False
