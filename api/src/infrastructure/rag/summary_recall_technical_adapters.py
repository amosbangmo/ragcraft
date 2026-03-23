"""Thin technical adapters for :mod:`application.use_cases.chat.orchestration.summary_recall_workflow`."""

from __future__ import annotations

from domain.projects.project import Project
from domain.rag.retrieval_filters import RetrievalFilters
from domain.rag.retrieval_settings import RetrievalSettings
from domain.rag.summary_recall_document import SummaryRecallDocument
from infrastructure.rag.summary_recall_document_adapter import summary_recall_document_from_langchain
from infrastructure.rag.docstore_service import DocStoreService
from infrastructure.rag.hybrid_retrieval_service import HybridRetrievalService
from infrastructure.rag.query_rewrite_service import QueryRewriteService
from infrastructure.rag.vectorstore_service import VectorStoreService


class QueryRewriteAdapter:
    """LLM-backed query rewrite (implements :class:`~application.use_cases.chat.orchestration.summary_recall_ports.QueryRewritePort`)."""

    def __init__(self, inner: QueryRewriteService) -> None:
        self._inner = inner

    def rewrite(
        self,
        *,
        question: str,
        chat_history: list[str],
        max_history_messages: int,
    ) -> str:
        return self._inner.rewrite(
            question=question,
            chat_history=chat_history,
            max_history_messages=max_history_messages,
        )


class SummaryVectorRecallAdapter:
    """FAISS summary-level similarity search."""

    def __init__(self, vectorstore_service: VectorStoreService) -> None:
        self._vectorstore = vectorstore_service

    def similarity_search(
        self,
        project: Project,
        query: str,
        k: int,
    ) -> list[SummaryRecallDocument]:
        return self._vectorstore.similarity_search(project, query, k=k)


class SummaryLexicalRecallAdapter:
    """BM25 over project assets for hybrid summary recall."""

    def __init__(
        self,
        docstore_service: DocStoreService,
        hybrid_retrieval_service: HybridRetrievalService,
    ) -> None:
        self._docstore = docstore_service
        self._hybrid = hybrid_retrieval_service

    def lexical_summary_search(
        self,
        *,
        project: Project,
        query: str,
        settings: RetrievalSettings,
        filters: RetrievalFilters | None,
    ) -> list[SummaryRecallDocument]:
        project_assets = self._docstore.list_assets_for_project(
            user_id=project.user_id,
            project_id=project.project_id,
        )
        bm25_lc = self._hybrid.lexical_search(
            query=query,
            assets=project_assets,
            k=settings.bm25_search_k,
            filters=filters,
            k1=settings.bm25_k1,
            b=settings.bm25_b,
            epsilon=settings.bm25_epsilon,
        )
        return [summary_recall_document_from_langchain(d) for d in bm25_lc]


__all__ = [
    "QueryRewriteAdapter",
    "SummaryLexicalRecallAdapter",
    "SummaryVectorRecallAdapter",
]
