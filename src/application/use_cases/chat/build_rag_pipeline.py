from __future__ import annotations

from time import perf_counter
from src.application.use_cases.chat.orchestration.recall_then_assemble_pipeline import (
    run_recall_then_assemble_pipeline,
)
from src.application.use_cases.chat.orchestration.ports import (
    PipelineAssemblyPort,
    PipelineBuildQueryLogEmitterPort,
    SummaryRecallStagePort,
)
from src.domain.pipeline_payloads import PipelineBuildResult
from src.domain.project import Project
from src.domain.retrieval_filters import RetrievalFilters
from src.domain.retrieval_settings_override_spec import RetrievalSettingsOverrideSpec


class BuildRagPipelineUseCase:
    """
    Build a full retrieval + prompt pipeline, optionally logging the retrieval stage.

    Query logging for this path is limited to the pipeline-build payload (no final answer);
    end-to-end ask flows may defer logging until after answer generation.
    """

    def __init__(
        self,
        *,
        summary_recall_service: SummaryRecallStagePort,
        pipeline_assembly_service: PipelineAssemblyPort,
        query_log_emitter: PipelineBuildQueryLogEmitterPort,
    ) -> None:
        self._summary_recall = summary_recall_service
        self._pipeline_assembly = pipeline_assembly_service
        self._query_log_emitter = query_log_emitter

    def execute(
        self,
        project: Project,
        question: str,
        chat_history: list[str] | None = None,
        *,
        emit_query_log: bool = True,
        filters: RetrievalFilters | None = None,
        retrieval_overrides: RetrievalSettingsOverrideSpec | None = None,
        enable_query_rewrite_override: bool | None = None,
        enable_hybrid_retrieval_override: bool | None = None,
    ) -> PipelineBuildResult | None:
        pipeline_started = perf_counter()
        payload = run_recall_then_assemble_pipeline(
            project=project,
            question=question,
            chat_history=chat_history,
            summary_recall_service=self._summary_recall,
            pipeline_assembly_service=self._pipeline_assembly,
            pipeline_started_monotonic=pipeline_started,
            filters=filters,
            retrieval_overrides=retrieval_overrides,
            enable_query_rewrite_override=enable_query_rewrite_override,
            enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
        )
        if payload is None:
            return None
        self._query_log_emitter.emit_after_pipeline_build(
            enabled=emit_query_log,
            project=project,
            question=question,
            payload=payload,
        )
        return payload
