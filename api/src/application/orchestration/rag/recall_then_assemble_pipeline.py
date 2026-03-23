from __future__ import annotations

from application.orchestration.rag.ports import PipelineAssemblyPort, SummaryRecallStagePort
from application.orchestration.rag.summary_recall_from_request import (
    run_summary_recall_from_chat_request,
)
from domain.projects.project import Project
from domain.rag.pipeline_payloads import PipelineBuildResult
from domain.rag.retrieval_filters import RetrievalFilters
from domain.rag.retrieval_settings_override_spec import RetrievalSettingsOverrideSpec


def run_recall_then_assemble_pipeline(
    *,
    project: Project,
    question: str,
    chat_history: list[str] | None,
    summary_recall_service: SummaryRecallStagePort,
    pipeline_assembly_service: PipelineAssemblyPort,
    pipeline_started_monotonic: float,
    filters: RetrievalFilters | None = None,
    retrieval_overrides: RetrievalSettingsOverrideSpec | None = None,
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
        retrieval_overrides=retrieval_overrides,
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
