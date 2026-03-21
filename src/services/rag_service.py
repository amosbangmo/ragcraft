from time import perf_counter
from typing import Any

from src.application.chat.use_cases.ask_question import AskQuestionUseCase
from src.application.common.pipeline_query_context import RAGPipelineQueryContext
from src.application.common.pipeline_query_log import build_query_log_ingress_payload
from src.application.common.safe_query_log import log_query_safely
from src.application.common.summary_recall_preview import SummaryRecallPreviewDTO
from src.domain.pipeline_latency import PipelineLatency
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
        self._ask_question = AskQuestionUseCase(
            build_pipeline=lambda *args, **kwargs: self.build_pipeline(*args, **kwargs),
            answer_generation_service=self.answer_generation_service,
            query_log_service=self.query_log_service,
        )

    @property
    def config(self) -> Any:
        return self.retrieval_settings_service.config_source

    @config.setter
    def config(self, value: Any) -> None:
        self.retrieval_settings_service.set_config_source(value)

    def _safe_log_query(self, payload: Any) -> None:
        log_query_safely(self.query_log_service, payload)

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
        return self._ask_question.execute(
            project,
            question,
            chat_history,
            filters=filters,
            retrieval_settings=retrieval_settings,
            enable_query_rewrite_override=enable_query_rewrite_override,
            enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
        )
