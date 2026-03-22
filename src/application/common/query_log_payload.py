from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class QueryLogIngressPayload:
    """
    Typed payload produced after a RAG pipeline run, before normalization in
    :class:`~src.backend.query_log_service.QueryLogService`.

    Mirrors the dict shape historically built in ``RAGService`` for query logging.
    """

    question: str
    rewritten_query: str
    project_id: str
    user_id: str
    selected_doc_ids: tuple[str, ...]
    retrieved_doc_ids: tuple[str, ...]
    latency_ms: float
    confidence: float
    hybrid_retrieval_enabled: bool
    retrieval_mode: str
    query_intent: str
    table_aware_qa_enabled: bool
    retrieval_strategy: dict[str, Any]
    context_compression_chars_before: int
    context_compression_chars_after: int
    context_compression_ratio: float
    section_expansion_count: int
    expanded_assets_count: int
    query_rewrite_ms: float
    retrieval_ms: float
    reranking_ms: float
    prompt_build_ms: float
    answer_generation_ms: float
    total_latency_ms: float
    answer: str | None = None

    def to_log_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "question": self.question,
            "rewritten_query": self.rewritten_query,
            "project_id": self.project_id,
            "user_id": self.user_id,
            "selected_doc_ids": list(self.selected_doc_ids),
            "retrieved_doc_ids": list(self.retrieved_doc_ids),
            "latency_ms": self.latency_ms,
            "confidence": self.confidence,
            "hybrid_retrieval_enabled": self.hybrid_retrieval_enabled,
            "retrieval_mode": self.retrieval_mode,
            "query_intent": self.query_intent,
            "table_aware_qa_enabled": self.table_aware_qa_enabled,
            "retrieval_strategy": dict(self.retrieval_strategy),
            "context_compression_chars_before": self.context_compression_chars_before,
            "context_compression_chars_after": self.context_compression_chars_after,
            "context_compression_ratio": self.context_compression_ratio,
            "section_expansion_count": self.section_expansion_count,
            "expanded_assets_count": self.expanded_assets_count,
            "query_rewrite_ms": self.query_rewrite_ms,
            "retrieval_ms": self.retrieval_ms,
            "reranking_ms": self.reranking_ms,
            "prompt_build_ms": self.prompt_build_ms,
            "answer_generation_ms": self.answer_generation_ms,
            "total_latency_ms": self.total_latency_ms,
        }
        if self.answer is not None:
            out["answer"] = self.answer
        return out
