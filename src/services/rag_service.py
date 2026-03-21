from time import perf_counter
from typing import Any

from src.application.common.pipeline_query_context import RAGPipelineQueryContext
from src.application.common.query_log_payload import QueryLogIngressPayload
from src.application.common.summary_recall_preview import SummaryRecallPreviewDTO
from src.domain.pipeline_latency import PipelineLatency, merge_with_answer_stage
from src.domain.pipeline_payloads import PipelineBuildResult, SummaryRecallResult
from src.domain.project import Project
from src.domain.rag_response import RAGResponse
from src.domain.retrieval_filters import RetrievalFilters
from src.services.answer_generation_service import AnswerGenerationService
from src.services.docstore_service import DocStoreService
from src.services.evaluation_service import EvaluationService
from src.services.pipeline_assembly_service import PipelineAssemblyService
from src.services.query_log_service import QueryLogService
from src.services.reranking_service import RerankingService
from src.services.retrieval_settings_service import RetrievalSettingsService
from src.services.summary_recall_service import SummaryRecallService
from src.services.table_qa_service import TableQAService
from src.services.vectorstore_service import VectorStoreService


def _preview_from_summary_recall(bundle: SummaryRecallResult) -> SummaryRecallPreviewDTO | None:
    if not bundle.recalled_summary_docs:
        return None
    return SummaryRecallPreviewDTO(
        rewritten_question=bundle.rewritten_question,
        recalled_summary_docs=bundle.recalled_summary_docs,
        vector_summary_docs=bundle.vector_summary_docs,
        bm25_summary_docs=bundle.bm25_summary_docs,
        retrieval_mode="faiss+bm25" if bundle.enable_hybrid_retrieval else "faiss",
        query_rewrite_enabled=bundle.enable_query_rewrite,
        hybrid_retrieval_enabled=bundle.enable_hybrid_retrieval,
        use_adaptive_retrieval=bundle.use_adaptive_retrieval,
    )


def _latency_fields_for_query_log(latency: PipelineLatency) -> dict[str, float]:
    d = latency.to_dict()
    return {
        "query_rewrite_ms": d["query_rewrite_ms"],
        "retrieval_ms": d["retrieval_ms"],
        "reranking_ms": d["reranking_ms"],
        "prompt_build_ms": d["prompt_build_ms"],
        "answer_generation_ms": d["answer_generation_ms"],
        "total_latency_ms": d["total_ms"],
    }


def _query_log_payload(
    *,
    project: Project,
    question: str,
    pipeline: PipelineBuildResult,
    latency: PipelineLatency,
    answer: str | None = None,
) -> QueryLogIngressPayload:
    section_expansion = pipeline.section_expansion
    context_compression = pipeline.context_compression
    stage = _latency_fields_for_query_log(latency)
    return QueryLogIngressPayload(
        question=question,
        rewritten_query=pipeline.rewritten_question,
        project_id=project.project_id,
        user_id=project.user_id,
        selected_doc_ids=tuple(pipeline.selected_doc_ids),
        retrieved_doc_ids=tuple(pipeline.recalled_doc_ids),
        latency_ms=latency.total_ms,
        confidence=pipeline.confidence,
        hybrid_retrieval_enabled=pipeline.hybrid_retrieval_enabled,
        retrieval_mode=pipeline.retrieval_mode,
        query_intent=pipeline.query_intent.value,
        table_aware_qa_enabled=pipeline.table_aware_qa_enabled,
        retrieval_strategy=pipeline.retrieval_strategy.to_dict(),
        context_compression_chars_before=context_compression.chars_before,
        context_compression_chars_after=context_compression.chars_after,
        context_compression_ratio=context_compression.ratio,
        section_expansion_count=section_expansion.section_expansion_count,
        expanded_assets_count=section_expansion.expanded_assets_count,
        query_rewrite_ms=stage["query_rewrite_ms"],
        retrieval_ms=stage["retrieval_ms"],
        reranking_ms=stage["reranking_ms"],
        prompt_build_ms=stage["prompt_build_ms"],
        answer_generation_ms=stage["answer_generation_ms"],
        total_latency_ms=stage["total_latency_ms"],
        answer=answer,
    )


class RAGService:
    """Orchestrates summary recall, pipeline assembly, answer generation, and query logging."""

    def __init__(
        self,
        vectorstore_service: VectorStoreService,
        evaluation_service: EvaluationService,
        docstore_service: DocStoreService,
        reranking_service: RerankingService,
        query_log_service: QueryLogService | None = None,
        retrieval_settings_service: RetrievalSettingsService | None = None,
        answer_generation_service: AnswerGenerationService | None = None,
    ):
        self.vectorstore_service = vectorstore_service
        self.evaluation_service = evaluation_service
        self.docstore_service = docstore_service
        self.reranking_service = reranking_service
        self.retrieval_settings_service = (
            retrieval_settings_service or RetrievalSettingsService()
        )
        self.table_qa_service = TableQAService()
        self.summary_recall_service = SummaryRecallService(
            vectorstore_service=vectorstore_service,
            docstore_service=docstore_service,
            retrieval_settings_service=self.retrieval_settings_service,
            table_qa_service=self.table_qa_service,
        )
        self.pipeline_assembly_service = PipelineAssemblyService(
            docstore_service=docstore_service,
            reranking_service=reranking_service,
            table_qa_service=self.table_qa_service,
        )
        self.query_log_service = query_log_service
        self.answer_generation_service = (
            answer_generation_service or AnswerGenerationService()
        )

    @property
    def config(self) -> Any:
        return self.retrieval_settings_service.config_source

    @config.setter
    def config(self, value: Any) -> None:
        self.retrieval_settings_service.set_config_source(value)

    def _safe_log_query(self, payload: QueryLogIngressPayload | dict[str, Any]) -> None:
        if self.query_log_service is None:
            return
        try:
            raw = payload.to_log_dict() if isinstance(payload, QueryLogIngressPayload) else payload
            self.query_log_service.log_query(payload=raw)
        except Exception:
            pass

    def build_chain(self, project: Project):
        """Returns the project vector store (chain cache compatibility)."""
        return self.vectorstore_service.load(project)

    def preview_summary_recall(
        self,
        project: Project,
        question: str,
        chat_history: list[str] | None = None,
        *,
        filters: RetrievalFilters | None = None,
        retrieval_settings: dict[str, Any] | None = None,
        enable_query_rewrite_override: bool | None = None,
        enable_hybrid_retrieval_override: bool | None = None,
    ) -> dict | None:
        ctx = RAGPipelineQueryContext.from_legacy(
            chat_history,
            filters=filters,
            retrieval_settings=retrieval_settings,
            enable_query_rewrite_override=enable_query_rewrite_override,
            enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
        )
        bundle = self.summary_recall_service.summary_recall_stage(
            project,
            question,
            list(ctx.chat_history),
            enable_query_rewrite_override=ctx.enable_query_rewrite_override,
            enable_hybrid_retrieval_override=ctx.enable_hybrid_retrieval_override,
            filters=ctx.filters,
            retrieval_settings=ctx.retrieval_settings,
        )
        preview = _preview_from_summary_recall(bundle)
        return preview.to_dict() if preview is not None else None

    def build_pipeline(
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
        bundle = self.summary_recall_service.summary_recall_stage(
            project,
            question,
            list(ctx.chat_history),
            enable_query_rewrite_override=ctx.enable_query_rewrite_override,
            enable_hybrid_retrieval_override=ctx.enable_hybrid_retrieval_override,
            filters=ctx.filters,
            retrieval_settings=ctx.retrieval_settings,
        )
        payload = self.pipeline_assembly_service.build(
            project=project,
            question=question,
            chat_history=chat_history or [],
            recall=bundle,
            pipeline_started_monotonic=pipeline_started,
        )
        if payload is None:
            return None
        if self.query_log_service is not None and emit_query_log:
            latency = PipelineLatency.from_dict(payload.latency)
            self._safe_log_query(
                _query_log_payload(
                    project=project,
                    question=question,
                    pipeline=payload,
                    latency=latency,
                )
            )
        return payload

    def inspect_pipeline(
        self,
        project: Project,
        question: str,
        chat_history: list[str] | None = None,
        *,
        filters: RetrievalFilters | None = None,
        retrieval_settings: dict[str, Any] | None = None,
        enable_query_rewrite_override: bool | None = None,
        enable_hybrid_retrieval_override: bool | None = None,
    ) -> PipelineBuildResult | None:
        return self.build_pipeline(
            project,
            question,
            chat_history,
            emit_query_log=False,
            filters=filters,
            retrieval_settings=retrieval_settings,
            enable_query_rewrite_override=enable_query_rewrite_override,
            enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
        )

    def generate_answer_from_pipeline(
        self, *, project: Project, pipeline: PipelineBuildResult
    ) -> str:
        return self.answer_generation_service.generate_answer(
            project=project, pipeline=pipeline
        )

    def ask(
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
        defer_log = self.query_log_service is not None
        pipeline = self.build_pipeline(
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
        answer = self.answer_generation_service.generate_answer(
            project=project, pipeline=pipeline
        )
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
            self._safe_log_query(
                _query_log_payload(
                    project=project,
                    question=question,
                    pipeline=pipeline,
                    latency=full_latency,
                    answer=answer,
                )
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
