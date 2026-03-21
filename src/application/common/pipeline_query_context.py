from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.domain.retrieval_filters import RetrievalFilters


@dataclass(frozen=True)
class RAGPipelineQueryContext:
    """
    Cross-layer inputs shared by RAG preview, pipeline build, and ask flows.

    Bundles the optional knobs that were previously passed as parallel kwargs on
    :class:`~src.services.rag_service.RAGService`.
    """

    chat_history: tuple[str, ...]
    filters: RetrievalFilters | None
    retrieval_settings: dict[str, Any] | None
    enable_query_rewrite_override: bool | None
    enable_hybrid_retrieval_override: bool | None

    @staticmethod
    def from_legacy(
        chat_history: list[str] | None,
        *,
        filters: RetrievalFilters | None,
        retrieval_settings: dict[str, Any] | None,
        enable_query_rewrite_override: bool | None,
        enable_hybrid_retrieval_override: bool | None,
    ) -> RAGPipelineQueryContext:
        return RAGPipelineQueryContext(
            chat_history=tuple(chat_history or ()),
            filters=filters,
            retrieval_settings=retrieval_settings,
            enable_query_rewrite_override=enable_query_rewrite_override,
            enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
        )
