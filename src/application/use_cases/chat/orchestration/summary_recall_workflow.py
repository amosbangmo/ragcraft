"""
Application-owned sequencing for the summary-recall stage.

Order: resolve settings → optional query rewrite → intent + table flag → execution plan →
vector recall → optional lexical recall → RRF merge → :class:`~src.domain.pipeline_payloads.SummaryRecallResult`.
"""

from __future__ import annotations

import logging
from dataclasses import replace
from time import perf_counter
from src.application.rag.dtos.recall_stages import VectorLexicalRecallBundle
from src.application.settings.retrieval_settings_tuner import RetrievalSettingsTuner
from src.application.use_cases.chat.orchestration.summary_recall_ports import (
    SummaryRecallTechnicalPorts,
    merge_summary_recall_documents,
)
from src.domain.pipeline_payloads import SummaryRecallResult
from src.domain.project import Project
from src.domain.retrieval.query_intent_classification import classify_query_intent
from src.domain.retrieval.summary_recall_execution_plan import resolve_summary_recall_execution_plan
from src.domain.retrieval.table_qa_policy import is_table_focused_question
from src.domain.retrieval_filters import (
    RetrievalFilters,
    filter_summary_documents_by_filters,
    vector_search_fetch_k,
)
from src.domain.retrieval_settings import RetrievalSettings
from src.domain.retrieval_settings_override_spec import RetrievalSettingsOverrideSpec
from src.domain.summary_recall_document import SummaryRecallDocument

logger = logging.getLogger(__name__)


class ApplicationSummaryRecallStage:
    """
    Implements :class:`~src.application.use_cases.chat.orchestration.ports.SummaryRecallStagePort`.

    Sequencing lives here; ``technical_ports`` hold LLM rewrite, FAISS, and BM25 operations.
    """

    def __init__(
        self,
        *,
        settings_tuner: RetrievalSettingsTuner,
        technical_ports: SummaryRecallTechnicalPorts,
    ) -> None:
        self._settings_tuner = settings_tuner
        self.technical_ports = technical_ports

    def _merged_recall_settings(
        self,
        project: Project,
        retrieval_overrides: RetrievalSettingsOverrideSpec | None,
        *,
        enable_query_rewrite_override: bool | None,
        enable_hybrid_retrieval_override: bool | None,
    ) -> RetrievalSettings:
        tuner = self._settings_tuner
        settings = tuner.merge(
            tuner.from_project(project.user_id, project.project_id),
            retrieval_overrides.as_merge_mapping() if retrieval_overrides else None,
        )
        if enable_query_rewrite_override is not None:
            settings = replace(settings, enable_query_rewrite=enable_query_rewrite_override)
        if enable_hybrid_retrieval_override is not None:
            settings = replace(settings, enable_hybrid_retrieval=enable_hybrid_retrieval_override)
        return settings

    def fuse_vector_and_lexical_recalls(
        self,
        *,
        settings: RetrievalSettings,
        project: Project,
        retrieval_query: str,
        enable_hybrid_retrieval: bool,
        filters: RetrievalFilters | None,
        similarity_search_k: int | None,
    ) -> VectorLexicalRecallBundle:
        """
        Vector (+ optional BM25) summary recall and RRF fusion.

        Exposed for integration tests that patch this step without mocking individual ports.
        """
        k_vec = (
            int(similarity_search_k)
            if similarity_search_k is not None
            else int(settings.similarity_search_k)
        )
        k_vec = max(1, k_vec)
        fetch_k = vector_search_fetch_k(base_k=k_vec, filters=filters)
        vector_summary_docs = self.technical_ports.vector_recall.similarity_search(
            project,
            retrieval_query,
            fetch_k,
        )
        if filters is not None and not filters.is_empty():
            vector_summary_docs = filter_summary_documents_by_filters(
                vector_summary_docs,
                filters,
            )[:k_vec]

        bm25_summary_docs: list[SummaryRecallDocument] = []
        if enable_hybrid_retrieval:
            bm25_summary_docs = self.technical_ports.lexical_recall.lexical_summary_search(
                project=project,
                query=retrieval_query,
                settings=settings,
                filters=filters,
            )

        merged_limit = k_vec
        if enable_hybrid_retrieval:
            merged_limit += int(settings.hybrid_search_k)

        recalled_summary_docs = merge_summary_recall_documents(
            settings=settings,
            primary_docs=vector_summary_docs,
            secondary_docs=bm25_summary_docs,
            max_docs=merged_limit,
        )

        return VectorLexicalRecallBundle(
            vector_summary_docs=tuple(vector_summary_docs),
            bm25_summary_docs=tuple(bm25_summary_docs),
            recalled_summary_docs=tuple(recalled_summary_docs),
        )

    def summary_recall_stage(
        self,
        project: Project,
        question: str,
        chat_history: list[str],
        *,
        enable_query_rewrite_override: bool | None = None,
        enable_hybrid_retrieval_override: bool | None = None,
        filters: RetrievalFilters | None = None,
        retrieval_overrides: RetrievalSettingsOverrideSpec | None = None,
    ) -> SummaryRecallResult:
        settings = self._merged_recall_settings(
            project,
            retrieval_overrides,
            enable_query_rewrite_override=enable_query_rewrite_override,
            enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
        )

        logger.debug(
            "Retrieval settings (project_id=%s): %s",
            project.project_id,
            settings.to_log_dict(),
        )

        enable_query_rewrite = settings.enable_query_rewrite

        t0 = perf_counter()
        if enable_query_rewrite:
            rewritten_question = self.technical_ports.query_rewrite.rewrite(
                question=question,
                chat_history=chat_history,
                max_history_messages=settings.query_rewrite_max_history_messages,
            )
        else:
            rewritten_question = question
        query_rewrite_ms = (perf_counter() - t0) * 1000.0

        query_intent = classify_query_intent(rewritten_question)
        table_aware_qa_enabled = is_table_focused_question(
            query_intent=query_intent,
            question=rewritten_question,
        )

        strategy, enable_hybrid_retrieval, similarity_search_k, use_adaptive_retrieval = (
            resolve_summary_recall_execution_plan(
                settings=settings,
                intent=query_intent,
                rewritten_query=rewritten_question,
                enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
            )
        )

        filters_for_retrieval = (
            filters if filters is not None and not filters.is_empty() else None
        )

        t1 = perf_counter()
        retrieval_payload = self.fuse_vector_and_lexical_recalls(
            settings=settings,
            project=project,
            retrieval_query=rewritten_question,
            enable_hybrid_retrieval=enable_hybrid_retrieval,
            filters=filters_for_retrieval,
            similarity_search_k=similarity_search_k,
        )
        retrieval_ms = (perf_counter() - t1) * 1000.0

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
            vector_summary_docs=list(retrieval_payload.vector_summary_docs),
            bm25_summary_docs=list(retrieval_payload.bm25_summary_docs),
            recalled_summary_docs=list(retrieval_payload.recalled_summary_docs),
            retrieval_ms=retrieval_ms,
        )
