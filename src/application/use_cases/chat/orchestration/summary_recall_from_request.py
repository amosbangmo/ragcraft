"""Shared summary-recall invocation for pipeline build and preview (single orchestration path)."""

from __future__ import annotations

from typing import Any

from src.application.common.pipeline_query_context import RAGPipelineQueryContext
from src.application.use_cases.chat.orchestration.ports import SummaryRecallStagePort
from src.domain.pipeline_payloads import SummaryRecallResult
from src.domain.project import Project
from src.domain.retrieval_filters import RetrievalFilters


def run_summary_recall_from_chat_request(
    *,
    summary_recall_service: SummaryRecallStagePort,
    project: Project,
    question: str,
    chat_history: list[str] | None,
    filters: RetrievalFilters | None = None,
    retrieval_settings: dict[str, Any] | None = None,
    enable_query_rewrite_override: bool | None = None,
    enable_hybrid_retrieval_override: bool | None = None,
) -> SummaryRecallResult:
    """
    Build :class:`~src.application.common.pipeline_query_context.RAGPipelineQueryContext` from
    transport kwargs and run :meth:`SummaryRecallStagePort.summary_recall_stage`.
    """
    ctx = RAGPipelineQueryContext.from_chat_request(
        chat_history,
        filters=filters,
        retrieval_settings=retrieval_settings,
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
        retrieval_settings=ctx.retrieval_settings,
    )
