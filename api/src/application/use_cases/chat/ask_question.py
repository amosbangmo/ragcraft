from __future__ import annotations

from time import perf_counter
from application.common.safe_query_log import log_query_safely
from application.common.pipeline_query_log import build_query_log_ingress_payload
from domain.rag.pipeline_latency import merge_with_answer_stage
from domain.projects.project import Project
from domain.rag.rag_response import RAGResponse
from domain.rag.retrieval_filters import RetrievalFilters
from domain.common.ports import GenerationPort, QueryLogPort, RetrievalPort
from domain.rag.retrieval_settings_override_spec import RetrievalSettingsOverrideSpec


class AskQuestionUseCase:
    """
    End-to-end RAG ask: build pipeline via :class:`~domain.common.ports.RetrievalPort`,
    generate answer via :class:`~domain.common.ports.GenerationPort`, merge latency,
    emit deferred query log via :class:`~domain.common.ports.QueryLogPort`,
    return :class:`~domain.rag_response.RAGResponse`.
    """

    def __init__(
        self,
        *,
        retrieval: RetrievalPort,
        generation: GenerationPort,
        query_log: QueryLogPort | None,
    ) -> None:
        self._retrieval = retrieval
        self._generation = generation
        self._query_log = query_log

    def execute(
        self,
        project: Project,
        question: str,
        chat_history: list[str] | None = None,
        *,
        filters: RetrievalFilters | None = None,
        retrieval_overrides: RetrievalSettingsOverrideSpec | None = None,
        enable_query_rewrite_override: bool | None = None,
        enable_hybrid_retrieval_override: bool | None = None,
    ) -> RAGResponse | None:
        ask_started = perf_counter()
        defer_log = self._query_log is not None
        pipeline = self._retrieval.execute(
            project,
            question,
            chat_history,
            emit_query_log=not defer_log,
            filters=filters,
            retrieval_overrides=retrieval_overrides,
            enable_query_rewrite_override=enable_query_rewrite_override,
            enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
        )
        if pipeline is None:
            return None

        gen_started = perf_counter()
        answer = self._generation.generate_answer(project=project, pipeline=pipeline)
        answer_generation_ms = (perf_counter() - gen_started) * 1000.0
        total_ms = (perf_counter() - ask_started) * 1000.0
        full_latency = merge_with_answer_stage(
            pipeline.latency,
            answer_generation_ms=answer_generation_ms,
            total_ms=total_ms,
        )
        pipeline.latency = full_latency
        pipeline.latency_ms = total_ms

        if defer_log:
            log_query_safely(
                self._query_log,
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
            latency=full_latency,
        )
