from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langchain_core.documents import Document


@dataclass(frozen=True)
class SummaryRecallPreviewDTO:
    """
    Serializable preview of the summary-recall stage (retrieval before full pipeline assembly).

    ``to_dict`` preserves the legacy dict contract returned to Streamlit / the app facade.
    """

    rewritten_question: str
    recalled_summary_docs: list[Document]
    vector_summary_docs: list[Document]
    bm25_summary_docs: list[Document]
    retrieval_mode: str
    query_rewrite_enabled: bool
    hybrid_retrieval_enabled: bool
    use_adaptive_retrieval: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "rewritten_question": self.rewritten_question,
            "recalled_summary_docs": self.recalled_summary_docs,
            "vector_summary_docs": self.vector_summary_docs,
            "bm25_summary_docs": self.bm25_summary_docs,
            "retrieval_mode": self.retrieval_mode,
            "query_rewrite_enabled": self.query_rewrite_enabled,
            "hybrid_retrieval_enabled": self.hybrid_retrieval_enabled,
            "use_adaptive_retrieval": self.use_adaptive_retrieval,
        }
