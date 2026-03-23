from __future__ import annotations

from dataclasses import dataclass

from domain.rag.summary_recall_document import SummaryRecallDocument


@dataclass(frozen=True)
class SummaryRecallPreviewDTO:
    """Preview of the summary-recall stage (retrieval before full pipeline assembly)."""

    rewritten_question: str
    recalled_summary_docs: list[SummaryRecallDocument]
    vector_summary_docs: list[SummaryRecallDocument]
    bm25_summary_docs: list[SummaryRecallDocument]
    retrieval_mode: str
    query_rewrite_enabled: bool
    hybrid_retrieval_enabled: bool
    use_adaptive_retrieval: bool
