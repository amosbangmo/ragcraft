from __future__ import annotations

from time import perf_counter

from application.orchestration.rag.ports import (
    PipelineAssemblyPort,
    PipelineBuildQueryLogEmitterPort,
    SummaryRecallStagePort,
)
from application.orchestration.rag.recall_then_assemble_pipeline import (
    run_recall_then_assemble_pipeline,
)
from domain.projects.project import Project
from domain.rag.pipeline_payloads import PipelineBuildResult
from domain.rag.retrieval_filters import RetrievalFilters
from domain.rag.retrieval_settings_override_spec import RetrievalSettingsOverrideSpec


class BuildRagPipelineUseCase:
    """
    **Shared build engine** for ask and inspect: recall → assembly →
    :class:`~domain.rag.pipeline_payloads.PipelineBuildResult`.

    Product query logging is optional and controlled only by ``emit_query_log``:
    when ``True``, emits a **pipeline-stage** log (no answer) via
    :class:`~application.orchestration.rag.ports.PipelineBuildQueryLogEmitterPort`.
    **Inspect** and **evaluation** callers must pass ``emit_query_log=False``; **ask**
    coordinates logging via :class:`~application.use_cases.chat.ask_question.AskQuestionUseCase`.
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
