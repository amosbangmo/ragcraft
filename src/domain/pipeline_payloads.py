from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from src.domain.query_intent import QueryIntent
from src.domain.retrieval_filters import RetrievalFilters
from src.domain.retrieval_strategy import RetrievalStrategy
from src.domain.summary_recall_document import SummaryRecallDocument

if TYPE_CHECKING:
    from src.domain.retrieval_settings import RetrievalSettings


@dataclass
class SectionExpansionStats:
    enabled: bool = False
    applied: bool = False
    section_expansion_count: int = 0
    expanded_assets_count: int = 0
    recall_pool_size: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "applied": self.applied,
            "section_expansion_count": self.section_expansion_count,
            "expanded_assets_count": self.expanded_assets_count,
            "recall_pool_size": self.recall_pool_size,
        }


@dataclass
class ContextCompressionStats:
    enabled: bool = False
    applied: bool = False
    chars_before: int = 0
    chars_after: int = 0
    ratio: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "applied": self.applied,
            "chars_before": self.chars_before,
            "chars_after": self.chars_after,
            "ratio": self.ratio,
        }


@dataclass
class SummaryRecallResult:
    settings: RetrievalSettings
    rewritten_question: str
    query_rewrite_ms: float
    query_intent: QueryIntent
    table_aware_qa_enabled: bool
    use_adaptive_retrieval: bool
    strategy: RetrievalStrategy
    enable_hybrid_retrieval: bool
    enable_query_rewrite: bool
    filters_for_retrieval: RetrievalFilters | None
    vector_summary_docs: list[SummaryRecallDocument]
    bm25_summary_docs: list[SummaryRecallDocument]
    recalled_summary_docs: list[SummaryRecallDocument]
    retrieval_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "settings": self.settings,
            "rewritten_question": self.rewritten_question,
            "query_rewrite_ms": self.query_rewrite_ms,
            "query_intent": self.query_intent.value,
            "table_aware_qa_enabled": self.table_aware_qa_enabled,
            "use_adaptive_retrieval": self.use_adaptive_retrieval,
            "strategy": self.strategy,
            "enable_hybrid_retrieval": self.enable_hybrid_retrieval,
            "enable_query_rewrite": self.enable_query_rewrite,
            "filters_for_retrieval": self.filters_for_retrieval,
            "vector_summary_docs": self.vector_summary_docs,
            "bm25_summary_docs": self.bm25_summary_docs,
            "recalled_summary_docs": self.recalled_summary_docs,
            "retrieval_ms": self.retrieval_ms,
        }


@dataclass
class PipelineBuildResult:
    question: str = ""
    rewritten_question: str = ""
    query_intent: QueryIntent = QueryIntent.UNKNOWN
    table_aware_qa_enabled: bool = False
    chat_history: list[str] = field(default_factory=list)
    retrieval_mode: str = "faiss"
    query_rewrite_enabled: bool = False
    hybrid_retrieval_enabled: bool = False
    adaptive_retrieval_enabled: bool = False
    retrieval_strategy: RetrievalStrategy = field(
        default_factory=lambda: RetrievalStrategy(k=1, use_hybrid=False, apply_filters=True)
    )
    retrieval_filters: dict[str, Any] | None = None
    vector_summary_docs: list[SummaryRecallDocument] = field(default_factory=list)
    bm25_summary_docs: list[SummaryRecallDocument] = field(default_factory=list)
    recalled_summary_docs: list[SummaryRecallDocument] = field(default_factory=list)
    recalled_doc_ids: list[str] = field(default_factory=list)
    recalled_raw_assets: list[dict[str, Any]] = field(default_factory=list)
    pre_rerank_raw_assets: list[dict[str, Any]] = field(default_factory=list)
    section_expansion: SectionExpansionStats = field(default_factory=SectionExpansionStats)
    selected_summary_docs: list[SummaryRecallDocument] = field(default_factory=list)
    selected_doc_ids: list[str] = field(default_factory=list)
    reranked_raw_assets: list[dict[str, Any]] = field(default_factory=list)
    prompt_context_assets: list[dict[str, Any]] = field(default_factory=list)
    context_compression: ContextCompressionStats = field(default_factory=ContextCompressionStats)
    prompt_sources: list[dict[str, Any]] = field(default_factory=list)
    image_context_enriched: bool = False
    multimodal_analysis: dict[str, Any] = field(default_factory=dict)
    multimodal_orchestration_hint: str | None = None
    raw_context: str = ""
    prompt: str = ""
    confidence: float = 0.0
    latency: dict[str, float] = field(default_factory=dict)
    latency_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "rewritten_question": self.rewritten_question,
            "query_intent": self.query_intent.value,
            "table_aware_qa_enabled": self.table_aware_qa_enabled,
            "chat_history": list(self.chat_history),
            "retrieval_mode": self.retrieval_mode,
            "query_rewrite_enabled": self.query_rewrite_enabled,
            "hybrid_retrieval_enabled": self.hybrid_retrieval_enabled,
            "adaptive_retrieval_enabled": self.adaptive_retrieval_enabled,
            "retrieval_strategy": self.retrieval_strategy.to_dict(),
            "retrieval_filters": self.retrieval_filters,
            "vector_summary_docs": self.vector_summary_docs,
            "bm25_summary_docs": self.bm25_summary_docs,
            "recalled_summary_docs": self.recalled_summary_docs,
            "recalled_doc_ids": list(self.recalled_doc_ids),
            "recalled_raw_assets": self.recalled_raw_assets,
            "pre_rerank_raw_assets": self.pre_rerank_raw_assets,
            "section_expansion": self.section_expansion.to_dict(),
            "selected_summary_docs": self.selected_summary_docs,
            "selected_doc_ids": list(self.selected_doc_ids),
            "reranked_raw_assets": self.reranked_raw_assets,
            "prompt_context_assets": self.prompt_context_assets,
            "context_compression": self.context_compression.to_dict(),
            "prompt_sources": self.prompt_sources,
            "image_context_enriched": self.image_context_enriched,
            "multimodal_analysis": dict(self.multimodal_analysis),
            "multimodal_orchestration_hint": self.multimodal_orchestration_hint,
            "raw_context": self.raw_context,
            "prompt": self.prompt,
            "confidence": self.confidence,
            "latency": dict(self.latency),
            "latency_ms": self.latency_ms,
        }
