"""Shared summary-recall invocation for pipeline build and preview (single orchestration path)."""

from __future__ import annotations

from application.common.pipeline_query_context import RAGPipelineQueryContext
from application.orchestration.rag.ports import SummaryRecallStagePort
from domain.projects.project import Project
from domain.rag.pipeline_payloads import SummaryRecallResult
from domain.rag.retrieval_filters import RetrievalFilters
from domain.rag.retrieval_settings_override_spec import RetrievalSettingsOverrideSpec


def run_summary_recall_from_chat_request(
    *,
    summary_recall_service: SummaryRecallStagePort,
    project: Project,
    question: str,
    chat_history: list[str] | None,
    filters: RetrievalFilters | None = None,
    retrieval_overrides: RetrievalSettingsOverrideSpec | None = None,
    enable_query_rewrite_override: bool | None = None,
    enable_hybrid_retrieval_override: bool | None = None,
) -> SummaryRecallResult:
    """
    Build :class:`~application.common.pipeline_query_context.RAGPipelineQueryContext` from
    transport kwargs and run :meth:`SummaryRecallStagePort.summary_recall_stage`.
    """
    ctx = RAGPipelineQueryContext.from_chat_request(
        chat_history,
        filters=filters,
        retrieval_overrides=retrieval_overrides,
        enable_query_rewrite_override=enable_query_rewrite_override,
        enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
    )
    return summary_recall_service.summary_recall_stage(
        project,
        question,
        list(ctx.chat_history),
        enable_query_rewrite_override=ctx.enable_query_rewrite_override,
        enable_hybrid_retrieval_override=ctx.enable_hybrid_retrieval_override,
        filters=ctx.filters,
        retrieval_overrides=ctx.retrieval_overrides,
    )
