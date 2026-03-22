from __future__ import annotations

import logging
from dataclasses import replace
from time import perf_counter
from typing import Any

from langchain_core.documents import Document

from src.application.chat.policies.summary_document_fusion import merge_summary_documents_weighted_rrf
from src.core.config import RETRIEVAL_CONFIG
from src.domain.pipeline_payloads import SummaryRecallResult
from src.domain.project import Project
from src.domain.query_intent import QueryIntent
from src.domain.retrieval_filters import (
    RetrievalFilters,
    filter_summary_documents_by_filters,
    vector_search_fetch_k,
)
from src.domain.retrieval_settings import RetrievalSettings
from src.domain.retrieval_strategy import RetrievalStrategy
from src.infrastructure.services.adaptive_retrieval_service import AdaptiveRetrievalService
from src.infrastructure.services.docstore_service import DocStoreService
from src.infrastructure.services.hybrid_retrieval_service import HybridRetrievalService
from src.infrastructure.services.query_intent_service import QueryIntentService
from src.infrastructure.services.query_rewrite_service import QueryRewriteService
from src.infrastructure.services.retrieval_settings_service import RetrievalSettingsService
from src.infrastructure.services.table_qa_service import TableQAService
from src.infrastructure.services.vectorstore_service import VectorStoreService

logger = logging.getLogger(__name__)


class SummaryRecallService:
    """
    Query rewrite, intent classification, adaptive retrieval strategy, hybrid recall,
    and RRF merge over summary-level documents.
    """

    def __init__(
        self,
        vectorstore_service: VectorStoreService,
        docstore_service: DocStoreService,
        retrieval_settings_service: RetrievalSettingsService,
        table_qa_service: TableQAService,
    ) -> None:
        self.vectorstore_service = vectorstore_service
        self.docstore_service = docstore_service
        self.retrieval_settings_service = retrieval_settings_service
        self.table_qa_service = table_qa_service
        self.query_rewrite_service = QueryRewriteService(
            max_history_messages=RETRIEVAL_CONFIG.query_rewrite_max_history_messages
        )
        self.hybrid_retrieval_service = HybridRetrievalService(
            k1=RETRIEVAL_CONFIG.bm25_k1,
            b=RETRIEVAL_CONFIG.bm25_b,
            epsilon=RETRIEVAL_CONFIG.bm25_epsilon,
        )
        self.query_intent_service = QueryIntentService()
        self.adaptive_retrieval_service = AdaptiveRetrievalService()

    def _merged_recall_settings(
        self,
        project: Project,
        retrieval_settings: dict[str, Any] | None,
        *,
        enable_query_rewrite_override: bool | None,
        enable_hybrid_retrieval_override: bool | None,
    ) -> RetrievalSettings:
        rss = self.retrieval_settings_service
        settings = rss.merge(
            rss.from_project(project.user_id, project.project_id),
            retrieval_settings,
        )
        if enable_query_rewrite_override is not None:
            settings = replace(settings, enable_query_rewrite=enable_query_rewrite_override)
        if enable_hybrid_retrieval_override is not None:
            settings = replace(settings, enable_hybrid_retrieval=enable_hybrid_retrieval_override)
        return settings

    def _rewrite_and_classify(
        self,
        question: str,
        chat_history: list[str],
        *,
        settings: RetrievalSettings,
    ) -> tuple[str, float, QueryIntent, bool]:
        enable_query_rewrite = settings.enable_query_rewrite
        t0 = perf_counter()
        rewritten_question = self.rewrite_question(
            question,
            chat_history,
            enable_query_rewrite=enable_query_rewrite,
            settings=settings,
        )
        query_rewrite_ms = (perf_counter() - t0) * 1000.0

        query_intent = self.query_intent_service.classify(rewritten_question)
        table_aware_qa_enabled = self.table_qa_service.is_table_query(
            query_intent=query_intent,
            question=rewritten_question,
        )
        return rewritten_question, query_rewrite_ms, query_intent, table_aware_qa_enabled

    def _execution_plan_for_retrieval(
        self,
        *,
        settings: RetrievalSettings,
        query_intent: QueryIntent,
        rewritten_question: str,
        enable_hybrid_retrieval_override: bool | None,
    ) -> tuple[RetrievalStrategy, bool, int, bool]:
        use_adaptive_retrieval = enable_hybrid_retrieval_override is None
        if use_adaptive_retrieval:
            strategy = self.adaptive_retrieval_service.choose_strategy(
                settings=settings,
                intent=query_intent,
                rewritten_query=rewritten_question,
            )
            enable_hybrid_retrieval = strategy.use_hybrid
            similarity_search_k = strategy.k
        else:
            strategy = RetrievalStrategy(
                k=max(1, int(settings.similarity_search_k)),
                use_hybrid=bool(settings.enable_hybrid_retrieval),
                apply_filters=True,
            )
            enable_hybrid_retrieval = settings.enable_hybrid_retrieval
            similarity_search_k = strategy.k
        return strategy, enable_hybrid_retrieval, similarity_search_k, use_adaptive_retrieval

    def rewrite_question(
        self,
        question: str,
        chat_history: list[str],
        *,
        enable_query_rewrite: bool,
        settings: RetrievalSettings,
    ) -> str:
        if not enable_query_rewrite:
            return question

        return self.query_rewrite_service.rewrite(
            question=question,
            chat_history=chat_history,
            max_history_messages=settings.query_rewrite_max_history_messages,
        )

    def merge_summary_docs(
        self,
        *,
        settings: RetrievalSettings,
        primary_docs: list[Document],
        secondary_docs: list[Document],
        max_docs: int | None = None,
    ) -> list[Document]:
        """Thin adapter over :func:`merge_summary_documents_weighted_rrf`."""
        return merge_summary_documents_weighted_rrf(
            settings=settings,
            primary_docs=primary_docs,
            secondary_docs=secondary_docs,
            max_docs=max_docs,
        )

    def retrieve_summary_docs(
        self,
        *,
        settings: RetrievalSettings,
        project: Project,
        retrieval_query: str,
        enable_hybrid_retrieval: bool,
        filters: RetrievalFilters | None = None,
        similarity_search_k: int | None = None,
    ) -> dict[str, Any]:
        k_vec = (
            int(similarity_search_k)
            if similarity_search_k is not None
            else int(settings.similarity_search_k)
        )
        k_vec = max(1, k_vec)
        fetch_k = vector_search_fetch_k(base_k=k_vec, filters=filters)
        vector_summary_docs = self.vectorstore_service.similarity_search(
            project,
            retrieval_query,
            k=fetch_k,
        )
        if filters is not None and not filters.is_empty():
            vector_summary_docs = filter_summary_documents_by_filters(
                vector_summary_docs,
                filters,
            )[:k_vec]

        bm25_summary_docs: list[Document] = []

        if enable_hybrid_retrieval:
            project_assets = self.docstore_service.list_assets_for_project(
                user_id=project.user_id,
                project_id=project.project_id,
            )

            bm25_summary_docs = self.hybrid_retrieval_service.lexical_search(
                query=retrieval_query,
                assets=project_assets,
                k=settings.bm25_search_k,
                filters=filters,
                k1=settings.bm25_k1,
                b=settings.bm25_b,
                epsilon=settings.bm25_epsilon,
            )

        merged_limit = k_vec
        if enable_hybrid_retrieval:
            merged_limit += int(settings.hybrid_search_k)

        recalled_summary_docs = self.merge_summary_docs(
            settings=settings,
            primary_docs=vector_summary_docs,
            secondary_docs=bm25_summary_docs,
            max_docs=merged_limit,
        )

        return {
            "vector_summary_docs": vector_summary_docs,
            "bm25_summary_docs": bm25_summary_docs,
            "recalled_summary_docs": recalled_summary_docs,
        }

    def summary_recall_stage(
        self,
        project: Project,
        question: str,
        chat_history: list[str],
        *,
        enable_query_rewrite_override: bool | None = None,
        enable_hybrid_retrieval_override: bool | None = None,
        filters: RetrievalFilters | None = None,
        retrieval_settings: dict[str, Any] | None = None,
    ) -> SummaryRecallResult:
        settings = self._merged_recall_settings(
            project,
            retrieval_settings,
            enable_query_rewrite_override=enable_query_rewrite_override,
            enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
        )

        logger.debug(
            "Retrieval settings (project_id=%s): %s",
            project.project_id,
            settings.to_log_dict(),
        )

        enable_query_rewrite = settings.enable_query_rewrite

        rewritten_question, query_rewrite_ms, query_intent, table_aware_qa_enabled = (
            self._rewrite_and_classify(question, chat_history, settings=settings)
        )

        strategy, enable_hybrid_retrieval, similarity_search_k, use_adaptive_retrieval = (
            self._execution_plan_for_retrieval(
                settings=settings,
                query_intent=query_intent,
                rewritten_question=rewritten_question,
                enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
            )
        )

        filters_for_retrieval = (
            filters if filters is not None and not filters.is_empty() else None
        )

        t0 = perf_counter()
        retrieval_payload = self.retrieve_summary_docs(
            settings=settings,
            project=project,
            retrieval_query=rewritten_question,
            enable_hybrid_retrieval=enable_hybrid_retrieval,
            filters=filters_for_retrieval,
            similarity_search_k=similarity_search_k,
        )
        retrieval_ms = (perf_counter() - t0) * 1000.0

        return SummaryRecallResult(
            settings=settings,
            rewritten_question=rewritten_question,
            query_rewrite_ms=query_rewrite_ms,
            query_intent=query_intent,
            table_aware_qa_enabled=table_aware_qa_enabled,
            use_adaptive_retrieval=use_adaptive_retrieval,
            strategy=strategy,
            enable_hybrid_retrieval=enable_hybrid_retrieval,
            enable_query_rewrite=enable_query_rewrite,
            filters_for_retrieval=filters_for_retrieval,
            vector_summary_docs=retrieval_payload["vector_summary_docs"],
            bm25_summary_docs=retrieval_payload["bm25_summary_docs"],
            recalled_summary_docs=retrieval_payload["recalled_summary_docs"],
            retrieval_ms=retrieval_ms,
        )
