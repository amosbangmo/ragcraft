from __future__ import annotations

from time import perf_counter
from typing import Any

from src.application.common.pipeline_query_context import RAGPipelineQueryContext
from src.application.common.pipeline_query_log import build_query_log_ingress_payload
from src.application.common.safe_query_log import log_query_safely
from src.domain.pipeline_latency import PipelineLatency
from src.domain.pipeline_payloads import PipelineBuildResult
from src.domain.project import Project
from src.domain.retrieval_filters import RetrievalFilters
from src.services.pipeline_assembly_service import PipelineAssemblyService
from src.services.query_log_service import QueryLogService
from src.services.summary_recall_service import SummaryRecallService


class BuildPipelineUseCase:
    """
    Orchestrates summary recall + pipeline assembly, optionally emitting a query log row.
    """

    def __init__(
        self,
        *,
        summary_recall_service: SummaryRecallService,
        pipeline_assembly_service: PipelineAssemblyService,
        query_log_service: QueryLogService | None,
    ) -> None:
        self._summary_recall = summary_recall_service
        self._pipeline_assembly = pipeline_assembly_service
        self._query_log_service = query_log_service

    def execute(
        self,
        project: Project,
        question: str,
        chat_history: list[str] | None = None,
        *,
        emit_query_log: bool = True,
        filters: RetrievalFilters | None = None,
        retrieval_settings: dict[str, Any] | None = None,
        enable_query_rewrite_override: bool | None = None,
        enable_hybrid_retrieval_override: bool | None = None,
    ) -> PipelineBuildResult | None:
        pipeline_started = perf_counter()
        ctx = RAGPipelineQueryContext.from_legacy(
            chat_history,
            filters=filters,
            retrieval_settings=retrieval_settings,
            enable_query_rewrite_override=enable_query_rewrite_override,
            enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
        )
        bundle = self._summary_recall.summary_recall_stage(
            project,
            question,
            list(ctx.chat_history),
            enable_query_rewrite_override=ctx.enable_query_rewrite_override,
            enable_hybrid_retrieval_override=ctx.enable_hybrid_retrieval_override,
            filters=ctx.filters,
            retrieval_settings=ctx.retrieval_settings,
        )
        payload = self._pipeline_assembly.build(
            project=project,
            question=question,
            chat_history=chat_history or [],
            recall=bundle,
            pipeline_started_monotonic=pipeline_started,
        )
        if payload is None:
            return None
        if self._query_log_service is not None and emit_query_log:
            latency = PipelineLatency.from_dict(payload.latency)
            log_query_safely(
                self._query_log_service,
                build_query_log_ingress_payload(
                    project=project,
                    question=question,
                    pipeline=payload,
                    latency=latency,
                ),
            )
        return payload
