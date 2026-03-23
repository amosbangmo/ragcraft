"""Typed results for FAISS vs hybrid retrieval comparison (no LLM)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RetrievalModeComparisonRow:
    question: str
    rewritten_query: str
    faiss_recall_docs: int
    hybrid_recall_docs: int
    faiss_recall_doc_ids: int
    hybrid_recall_doc_ids: int
    faiss_prompt_assets: int
    hybrid_prompt_assets: int
    faiss_confidence: float
    hybrid_confidence: float
    faiss_latency_ms: float
    hybrid_latency_ms: float
    shared_doc_ids: int
    hybrid_only_doc_ids: int
    faiss_selected_doc_ids: int
    hybrid_selected_doc_ids: int
    faiss_has_pipeline: bool
    hybrid_has_pipeline: bool

    def to_json_row(self) -> dict[str, Any]:
        """Terminal JSON row for HTTP / export (stable keys)."""
        return {
            "question": self.question,
            "rewritten_query": self.rewritten_query,
            "faiss_recall_docs": self.faiss_recall_docs,
            "hybrid_recall_docs": self.hybrid_recall_docs,
            "faiss_recall_doc_ids": self.faiss_recall_doc_ids,
            "hybrid_recall_doc_ids": self.hybrid_recall_doc_ids,
            "faiss_prompt_assets": self.faiss_prompt_assets,
            "hybrid_prompt_assets": self.hybrid_prompt_assets,
            "faiss_confidence": self.faiss_confidence,
            "hybrid_confidence": self.hybrid_confidence,
            "faiss_latency_ms": self.faiss_latency_ms,
            "hybrid_latency_ms": self.hybrid_latency_ms,
            "shared_doc_ids": self.shared_doc_ids,
            "hybrid_only_doc_ids": self.hybrid_only_doc_ids,
            "faiss_selected_doc_ids": self.faiss_selected_doc_ids,
            "hybrid_selected_doc_ids": self.hybrid_selected_doc_ids,
            "faiss_has_pipeline": self.faiss_has_pipeline,
            "hybrid_has_pipeline": self.hybrid_has_pipeline,
        }


@dataclass(frozen=True)
class RetrievalModeComparisonSummary:
    total_questions: int
    query_rewrite_enabled: bool
    avg_faiss_recall_doc_ids: float
    avg_hybrid_recall_doc_ids: float
    avg_faiss_prompt_assets: float
    avg_hybrid_prompt_assets: float
    avg_faiss_confidence: float
    avg_hybrid_confidence: float
    avg_faiss_latency_ms: float
    avg_hybrid_latency_ms: float
    hybrid_wins_on_recall_doc_ids: int
    hybrid_wins_on_confidence: int
    hybrid_wins_on_prompt_assets: int

    def to_json_summary(self) -> dict[str, Any]:
        """Terminal JSON summary for HTTP."""
        return {
            "total_questions": self.total_questions,
            "query_rewrite_enabled": self.query_rewrite_enabled,
            "avg_faiss_recall_doc_ids": self.avg_faiss_recall_doc_ids,
            "avg_hybrid_recall_doc_ids": self.avg_hybrid_recall_doc_ids,
            "avg_faiss_prompt_assets": self.avg_faiss_prompt_assets,
            "avg_hybrid_prompt_assets": self.avg_hybrid_prompt_assets,
            "avg_faiss_confidence": self.avg_faiss_confidence,
            "avg_hybrid_confidence": self.avg_hybrid_confidence,
            "avg_faiss_latency_ms": self.avg_faiss_latency_ms,
            "avg_hybrid_latency_ms": self.avg_hybrid_latency_ms,
            "hybrid_wins_on_recall_doc_ids": self.hybrid_wins_on_recall_doc_ids,
            "hybrid_wins_on_confidence": self.hybrid_wins_on_confidence,
            "hybrid_wins_on_prompt_assets": self.hybrid_wins_on_prompt_assets,
        }


@dataclass(frozen=True)
class RetrievalModeComparisonResult:
    questions: tuple[str, ...]
    summary: RetrievalModeComparisonSummary
    rows: tuple[RetrievalModeComparisonRow, ...]
