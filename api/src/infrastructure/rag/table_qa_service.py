from __future__ import annotations

from domain.rag.query_intent import QueryIntent
from domain.rag.retrieval.table_qa_policy import (
    TABLE_QA_PROMPT_HINT,
    TABLE_QA_RERANK_BOOST,
    is_table_focused_question,
)


class TableQAService:
    """
    Table-aware QA helpers for reranking and prompt hints.

    Rules live in :mod:`domain.rag.retrieval.table_qa_policy`.
    """

    def is_table_query(self, *, query_intent: QueryIntent, question: str) -> bool:
        return is_table_focused_question(query_intent=query_intent, question=question)

    def table_priority_boost(self) -> float:
        """Additive rerank score bump for table assets when table QA mode is on (cross-encoder scale)."""
        return TABLE_QA_RERANK_BOOST

    def build_table_prompt_hint(self) -> str:
        return TABLE_QA_PROMPT_HINT
