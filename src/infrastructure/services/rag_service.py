"""
RAG transport-facing shell: vector store loading, retrieval settings, and chat use-case wiring.

Orchestration lives under ``src.application.chat`` (use cases + ``orchestration``). This class keeps
a stable object graph for :class:`~src.composition.backend_composition.BackendComposition`, Streamlit,
and code that still expects ``rag_service.inspect_pipeline`` / ``.ask`` / ``.build_pipeline``.
"""

from typing import Any

from src.application.chat.orchestration.pipeline_query_log_emitter import PipelineQueryLogEmitter
from src.application.chat.use_cases.ask_question import AskQuestionUseCase
from src.application.chat.use_cases.build_rag_pipeline import BuildRagPipelineUseCase
from src.application.chat.use_cases.generate_answer_from_pipeline import GenerateAnswerFromPipelineUseCase
from src.application.chat.use_cases.inspect_rag_pipeline import InspectRagPipelineUseCase
from src.application.chat.use_cases.preview_summary_recall import PreviewSummaryRecallUseCase
from src.domain.pipeline_payloads import PipelineBuildResult
from src.domain.project import Project
from src.domain.rag_response import RAGResponse
from src.domain.retrieval_filters import RetrievalFilters
from src.infrastructure.services.answer_generation_service import AnswerGenerationService
from src.infrastructure.services.docstore_service import DocStoreService
from src.infrastructure.services.evaluation_service import EvaluationService
from src.infrastructure.services.pipeline_assembly_service import PipelineAssemblyService
from src.infrastructure.services.query_log_service import QueryLogService
from src.infrastructure.services.reranking_service import RerankingService
from src.infrastructure.services.retrieval_settings_service import RetrievalSettingsService
from src.infrastructure.services.summary_recall_service import SummaryRecallService
from src.infrastructure.services.table_qa_service import TableQAService
from src.infrastructure.services.vectorstore_service import VectorStoreService


class RAGService:
    """Wires shared retrieval services to chat-layer use cases (not an orchestration god-object)."""

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

        self._pipeline_query_log_emitter = PipelineQueryLogEmitter(query_log_service)
        self._build_rag_pipeline_uc = BuildRagPipelineUseCase(
            summary_recall_service=self.summary_recall_service,
            pipeline_assembly_service=self.pipeline_assembly_service,
            query_log_emitter=self._pipeline_query_log_emitter,
        )
        self._inspect_pipeline_uc = InspectRagPipelineUseCase(
            build_rag_pipeline=self._build_rag_pipeline_uc,
        )
        self._preview_summary_recall_uc = PreviewSummaryRecallUseCase(
            summary_recall_service=self.summary_recall_service,
        )
        self._generate_answer_from_pipeline_uc = GenerateAnswerFromPipelineUseCase(
            answer_generation_service=self.answer_generation_service,
        )
        self._ask_question = AskQuestionUseCase(
            build_pipeline=lambda *args, **kwargs: self.build_pipeline(*args, **kwargs),
            answer_generation_service=self.answer_generation_service,
            query_log=self.query_log_service,
        )

    @property
    def ask_question_use_case(self) -> AskQuestionUseCase:
        return self._ask_question

    @property
    def inspect_pipeline_use_case(self) -> InspectRagPipelineUseCase:
        return self._inspect_pipeline_uc

    @property
    def preview_summary_recall_use_case(self) -> PreviewSummaryRecallUseCase:
        return self._preview_summary_recall_uc

    @property
    def build_rag_pipeline_use_case(self) -> BuildRagPipelineUseCase:
        """Explicit access for callers that need the pipeline builder without ``RAGService`` shortcuts."""
        return self._build_rag_pipeline_uc

    @property
    def generate_answer_from_pipeline_use_case(self) -> GenerateAnswerFromPipelineUseCase:
        return self._generate_answer_from_pipeline_uc

    @property
    def config(self) -> Any:
        return self.retrieval_settings_service.config_source

    @config.setter
    def config(self, value: Any) -> None:
        self.retrieval_settings_service.set_config_source(value)

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
        return self._preview_summary_recall_uc.execute(
            project,
            question,
            chat_history,
            filters=filters,
            retrieval_settings=retrieval_settings,
            enable_query_rewrite_override=enable_query_rewrite_override,
            enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
        )

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
        return self._build_rag_pipeline_uc.execute(
            project,
            question,
            chat_history,
            emit_query_log=emit_query_log,
            filters=filters,
            retrieval_settings=retrieval_settings,
            enable_query_rewrite_override=enable_query_rewrite_override,
            enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
        )

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
        return self._inspect_pipeline_uc.execute(
            project,
            question,
            chat_history,
            filters=filters,
            retrieval_settings=retrieval_settings,
            enable_query_rewrite_override=enable_query_rewrite_override,
            enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
        )

    def generate_answer_from_pipeline(
        self, *, project: Project, pipeline: PipelineBuildResult
    ) -> str:
        return self._generate_answer_from_pipeline_uc.execute(
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
