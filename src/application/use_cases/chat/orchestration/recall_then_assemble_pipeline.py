from __future__ import annotations

from typing import Any

from src.application.use_cases.chat.orchestration.ports import PipelineAssemblyPort, SummaryRecallStagePort
from src.application.use_cases.chat.orchestration.summary_recall_from_request import (
    run_summary_recall_from_chat_request,
)
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
    bundle = run_summary_recall_from_chat_request(
        summary_recall_service=summary_recall_service,
        project=project,
        question=question,
        chat_history=chat_history,
        filters=filters,
        retrieval_settings=retrieval_settings,
        enable_query_rewrite_override=enable_query_rewrite_override,
        enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
    )
    return pipeline_assembly_service.build(
        project=project,
        question=question,
        chat_history=chat_history or [],
        recall=bundle,
        pipeline_started_monotonic=pipeline_started_monotonic,
    )
