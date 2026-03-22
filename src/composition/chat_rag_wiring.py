"""
Wires RAG retrieval infrastructure services into chat use cases.

Called from :class:`~src.composition.application_container.BackendApplicationContainer` using
technical adapters from :class:`~src.composition.backend_composition.BackendComposition`.
Orchestration lives in application use cases; this module only constructs the object graph.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.application.use_cases.chat.ask_question import AskQuestionUseCase
from src.application.use_cases.chat.build_rag_pipeline import BuildRagPipelineUseCase
from src.application.use_cases.chat.generate_answer_from_pipeline import GenerateAnswerFromPipelineUseCase
from src.application.use_cases.chat.inspect_rag_pipeline import InspectRagPipelineUseCase
from src.application.use_cases.chat.orchestration.pipeline_query_log_emitter import PipelineQueryLogEmitter
from src.application.use_cases.chat.preview_summary_recall import PreviewSummaryRecallUseCase
from src.domain.ports import QueryLogPort
from src.infrastructure.adapters.rag.answer_generation_service import AnswerGenerationService
from src.infrastructure.adapters.rag.docstore_service import DocStoreService
from src.infrastructure.adapters.rag.pipeline_assembly_service import PipelineAssemblyService
from src.infrastructure.adapters.rag.retrieval_settings_service import RetrievalSettingsService
from src.infrastructure.adapters.rag.reranking_service import RerankingService
from src.infrastructure.adapters.rag.summary_recall_service import SummaryRecallService
from src.infrastructure.adapters.rag.table_qa_service import TableQAService
from src.infrastructure.adapters.rag.vectorstore_service import VectorStoreService


@dataclass
class RagRetrievalSubgraph:
    """Shared RAG infrastructure services (built alongside chat use-case wiring)."""

    table_qa_service: TableQAService
    summary_recall_service: SummaryRecallService
    pipeline_assembly_service: PipelineAssemblyService
    answer_generation_service: AnswerGenerationService
    retrieval_settings_service: RetrievalSettingsService

    @property
    def config(self) -> Any:
        return self.retrieval_settings_service.config_source

    @config.setter
    def config(self, value: Any) -> None:
        self.retrieval_settings_service.set_config_source(value)


def build_rag_retrieval_subgraph(
    *,
    vectorstore_service: VectorStoreService,
    docstore_service: DocStoreService,
    reranking_service: RerankingService,
    retrieval_settings_service: RetrievalSettingsService | None = None,
    answer_generation_service: AnswerGenerationService | None = None,
) -> RagRetrievalSubgraph:
    rs = retrieval_settings_service or RetrievalSettingsService()
    table_qa = TableQAService()
    summary = SummaryRecallService(
        vectorstore_service=vectorstore_service,
        docstore_service=docstore_service,
        retrieval_settings_service=rs,
        table_qa_service=table_qa,
    )
    pipeline = PipelineAssemblyService(
        docstore_service=docstore_service,
        reranking_service=reranking_service,
        table_qa_service=table_qa,
    )
    answer = answer_generation_service or AnswerGenerationService()
    return RagRetrievalSubgraph(
        table_qa_service=table_qa,
        summary_recall_service=summary,
        pipeline_assembly_service=pipeline,
        answer_generation_service=answer,
        retrieval_settings_service=rs,
    )


@dataclass(frozen=True)
class ChatRagUseCases:
    build_rag_pipeline: BuildRagPipelineUseCase
    inspect_rag_pipeline: InspectRagPipelineUseCase
    preview_summary_recall: PreviewSummaryRecallUseCase
    generate_answer_from_pipeline: GenerateAnswerFromPipelineUseCase
    ask_question: AskQuestionUseCase


def build_chat_rag_use_cases(
    subgraph: RagRetrievalSubgraph,
    *,
    query_log: QueryLogPort | None,
) -> ChatRagUseCases:
    emitter = PipelineQueryLogEmitter(query_log)
    build_uc = BuildRagPipelineUseCase(
        summary_recall_service=subgraph.summary_recall_service,
        pipeline_assembly_service=subgraph.pipeline_assembly_service,
        query_log_emitter=emitter,
    )
    inspect_uc = InspectRagPipelineUseCase(build_rag_pipeline=build_uc)
    preview_uc = PreviewSummaryRecallUseCase(summary_recall_service=subgraph.summary_recall_service)
    generate_uc = GenerateAnswerFromPipelineUseCase(
        answer_generation_service=subgraph.answer_generation_service
    )
    ask_uc = AskQuestionUseCase(
        build_pipeline=build_uc.execute,
        answer_generation_service=subgraph.answer_generation_service,
        query_log=query_log,
    )
    return ChatRagUseCases(
        build_rag_pipeline=build_uc,
        inspect_rag_pipeline=inspect_uc,
        preview_summary_recall=preview_uc,
        generate_answer_from_pipeline=generate_uc,
        ask_question=ask_uc,
    )


__all__ = [
    "ChatRagUseCases",
    "RagRetrievalSubgraph",
    "build_chat_rag_use_cases",
    "build_rag_retrieval_subgraph",
]
