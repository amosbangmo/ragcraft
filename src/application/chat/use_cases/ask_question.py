from __future__ import annotations

from collections.abc import Callable
from time import perf_counter
from typing import Any

from src.application.common.safe_query_log import log_query_safely
from src.application.common.pipeline_query_log import build_query_log_ingress_payload
from src.domain.pipeline_latency import PipelineLatency, merge_with_answer_stage
from src.domain.pipeline_payloads import PipelineBuildResult
from src.domain.project import Project
from src.domain.rag_response import RAGResponse
from src.domain.retrieval_filters import RetrievalFilters
from src.services.answer_generation_service import AnswerGenerationService
from src.services.query_log_service import QueryLogService


class AskQuestionUseCase:
    """
    End-to-end RAG ask: build pipeline via injected callable (typically
    :meth:`src.services.rag_service.RAGService.build_pipeline` → :class:`BuildRagPipelineUseCase`),
    generate answer, merge latency, emit deferred query log with answer payload, return
    :class:`~src.domain.rag_response.RAGResponse`.
    """

    def __init__(
        self,
        *,
        build_pipeline: Callable[..., PipelineBuildResult | None],
        answer_generation_service: AnswerGenerationService,
        query_log_service: QueryLogService | None,
    ) -> None:
        self._build_pipeline = build_pipeline
        self._answer_generation = answer_generation_service
        self._query_log_service = query_log_service

    def execute(
        self,
        project: Project,
        question: str,
        chat_history: list[str] | None = None,
        *,
        filters: RetrievalFilters | None = None,
        retrieval_settings: dict[str, Any] | None = None,
        enable_query_rewrite_override: bool | None = None,
        enable_hybrid_retrieval_override: bool | None = None,
    ) -> RAGResponse | None:
        ask_started = perf_counter()
        defer_log = self._query_log_service is not None
        pipeline = self._build_pipeline(
            project,
            question,
            chat_history,
            emit_query_log=not defer_log,
            filters=filters,
            retrieval_settings=retrieval_settings,
            enable_query_rewrite_override=enable_query_rewrite_override,
            enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
        )
        if pipeline is None:
            return None

        gen_started = perf_counter()
        answer = self._answer_generation.generate_answer(project=project, pipeline=pipeline)
        answer_generation_ms = (perf_counter() - gen_started) * 1000.0
        total_ms = (perf_counter() - ask_started) * 1000.0
        full_latency = merge_with_answer_stage(
            pipeline.latency,
            answer_generation_ms=answer_generation_ms,
            total_ms=total_ms,
        )
        full_latency_dict = full_latency.to_dict()
        pipeline.latency = full_latency_dict
        pipeline.latency_ms = total_ms

        if defer_log:
            log_query_safely(
                self._query_log_service,
                build_query_log_ingress_payload(
                    project=project,
                    question=question,
                    pipeline=pipeline,
                    latency=full_latency,
                    answer=answer,
                ),
            )

        return RAGResponse(
            question=question,
            answer=answer,
            source_documents=pipeline.selected_summary_docs,
            raw_assets=pipeline.reranked_raw_assets,
            prompt_sources=pipeline.prompt_sources,
            confidence=pipeline.confidence,
            latency=full_latency_dict,
        )
