from __future__ import annotations

from typing import Any

from src.application.use_cases.chat.orchestration.ports import PipelineAssemblyPort, SummaryRecallStagePort
from src.application.common.pipeline_query_context import RAGPipelineQueryContext
from src.domain.pipeline_payloads import PipelineBuildResult
from src.domain.project import Project
from src.domain.retrieval_filters import RetrievalFilters


def run_recall_then_assemble_pipeline(
    *,
    project: Project,
    question: str,
    chat_history: list[str] | None,
    summary_recall_service: SummaryRecallStagePort,
    pipeline_assembly_service: PipelineAssemblyPort,
    pipeline_started_monotonic: float,
    filters: RetrievalFilters | None = None,
    retrieval_settings: dict[str, Any] | None = None,
    enable_query_rewrite_override: bool | None = None,
    enable_hybrid_retrieval_override: bool | None = None,
) -> PipelineBuildResult | None:
    """
    Run summary-recall then pipeline assembly (no query logging).

    Latency accounting starts at ``pipeline_started_monotonic`` (``time.perf_counter()``).
    """
    ctx = RAGPipelineQueryContext.from_legacy(
        chat_history,
        filters=filters,
        retrieval_settings=retrieval_settings,
        enable_query_rewrite_override=enable_query_rewrite_override,
        enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
    )
    bundle = summary_recall_service.summary_recall_stage(
        project,
        question,
        list(ctx.chat_history),
        enable_query_rewrite_override=ctx.enable_query_rewrite_override,
        enable_hybrid_retrieval_override=ctx.enable_hybrid_retrieval_override,
        filters=ctx.filters,
        retrieval_settings=ctx.retrieval_settings,
    )
    return pipeline_assembly_service.build(
        project=project,
        question=question,
        chat_history=chat_history or [],
        recall=bundle,
        pipeline_started_monotonic=pipeline_started_monotonic,
    )
