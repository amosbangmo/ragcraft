"""
Wires RAG retrieval infrastructure services into chat use cases.

Called from :class:`~src.composition.application_container.BackendApplicationContainer` using
technical adapters from :class:`~src.composition.backend_composition.BackendComposition`.
Orchestration lives in application use cases; this module only constructs the object graph.

**Orchestration inventory (adjacent wiring):**

- Summary recall sequencing: :class:`~src.application.use_cases.chat.orchestration.summary_recall_workflow.ApplicationSummaryRecallStage`
  with technical ports from :mod:`src.infrastructure.adapters.rag.summary_recall_technical_adapters`.
- Post-recall assembly: :class:`~src.application.use_cases.chat.orchestration.application_pipeline_assembly.ApplicationPipelineAssembly`
  (application) with technical stage adapters in
  :mod:`src.infrastructure.adapters.rag.post_recall_stage_adapters` and multimodal hints from
  :mod:`src.application.chat.multimodal_prompt_hints`.

**Target ownership:** this file instantiates adapters and use cases only. Flow order for build/ask is owned by
``BuildRagPipelineUseCase``, ``AskQuestionUseCase``, and ``src/application/use_cases/chat/orchestration/*``.
``InspectRagPipelineUseCase`` shares the same :class:`~src.domain.ports.RetrievalPort` as ask but always calls
``execute(..., emit_query_log=False)``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.application.use_cases.chat.ask_question import AskQuestionUseCase
from src.application.use_cases.chat.build_rag_pipeline import BuildRagPipelineUseCase
from src.application.use_cases.chat.orchestration.application_pipeline_assembly import (
    ApplicationPipelineAssembly,
)
from src.application.use_cases.chat.generate_answer_from_pipeline import GenerateAnswerFromPipelineUseCase
from src.application.use_cases.chat.inspect_rag_pipeline import InspectRagPipelineUseCase
from src.application.use_cases.chat.orchestration.pipeline_query_log_emitter import PipelineQueryLogEmitter
from src.application.use_cases.chat.orchestration.ports import PostRecallStagePorts
from src.application.use_cases.chat.orchestration.summary_recall_ports import SummaryRecallTechnicalPorts
from src.application.use_cases.chat.orchestration.summary_recall_workflow import ApplicationSummaryRecallStage
from src.application.use_cases.chat.preview_summary_recall import PreviewSummaryRecallUseCase
from src.application.chat.multimodal_prompt_hints import MultimodalPromptHints
from src.domain.ports import QueryLogPort
from src.infrastructure.adapters.rag.answer_generation_service import AnswerGenerationService
from src.infrastructure.adapters.rag.docstore_service import DocStoreService
from src.infrastructure.adapters.rag.post_recall_stage_adapters import (
    AssetRerankingAdapter,
    ContextualCompressionAdapter,
    DocstoreRecallReadAdapter,
    LayoutGroupingAdapter,
    PostRecallStageServices,
    PromptRenderAdapter,
    PromptSourceBuildAdapter,
    RerankedConfidenceAdapter,
    SectionExpansionStageAdapter,
    TableQaAdjunctAdapter,
    build_post_recall_stage_services,
)
from src.core.config import RETRIEVAL_CONFIG
from src.infrastructure.adapters.rag.hybrid_retrieval_service import HybridRetrievalService
from src.infrastructure.adapters.rag.query_rewrite_service import QueryRewriteService
from src.infrastructure.adapters.rag.retrieval_settings_service import RetrievalSettingsService
from src.infrastructure.adapters.rag.reranking_service import RerankingService
from src.infrastructure.adapters.rag.summary_recall_technical_adapters import (
    QueryRewriteAdapter,
    SummaryLexicalRecallAdapter,
    SummaryVectorRecallAdapter,
)
from src.infrastructure.adapters.rag.table_qa_service import TableQAService
from src.infrastructure.adapters.rag.vectorstore_service import VectorStoreService


def post_recall_stage_ports_from_services(services: PostRecallStageServices) -> PostRecallStagePorts:
    """Bind concrete post-recall services to application port bundle (composition root)."""
    return PostRecallStagePorts(
        docstore_read=DocstoreRecallReadAdapter(services.docstore_service),
        section_expansion=SectionExpansionStageAdapter(services.section_retrieval_service),
        reranking=AssetRerankingAdapter(services.reranking_service),
        table_qa=TableQaAdjunctAdapter(services.table_qa_service),
        contextual_compression=ContextualCompressionAdapter(services.contextual_compression_service),
        prompt_sources=PromptSourceBuildAdapter(services.prompt_source_service),
        layout_grouping=LayoutGroupingAdapter(services.layout_context_service),
        multimodal_hints=services.multimodal_prompt_hints,
        prompt_render=PromptRenderAdapter(services.prompt_builder_service),
        confidence=RerankedConfidenceAdapter(services.confidence_service),
    )


@dataclass
class RagRetrievalSubgraph:
    """Shared RAG infrastructure services (built alongside chat use-case wiring)."""

    table_qa_service: TableQAService
    summary_recall_stage: ApplicationSummaryRecallStage
    pipeline_assembly: ApplicationPipelineAssembly
    post_recall_stage_services: PostRecallStageServices
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
    retrieval_settings_service: RetrievalSettingsService,
) -> RagRetrievalSubgraph:
    table_qa = TableQAService()
    query_rewrite = QueryRewriteService(
        max_history_messages=RETRIEVAL_CONFIG.query_rewrite_max_history_messages
    )
    hybrid = HybridRetrievalService(
        k1=RETRIEVAL_CONFIG.bm25_k1,
        b=RETRIEVAL_CONFIG.bm25_b,
        epsilon=RETRIEVAL_CONFIG.bm25_epsilon,
    )
    technical = SummaryRecallTechnicalPorts(
        query_rewrite=QueryRewriteAdapter(query_rewrite),
        vector_recall=SummaryVectorRecallAdapter(vectorstore_service),
        lexical_recall=SummaryLexicalRecallAdapter(docstore_service, hybrid),
    )
    summary = ApplicationSummaryRecallStage(
        settings_tuner=retrieval_settings_service,
        technical_ports=technical,
    )
    post_recall = build_post_recall_stage_services(
        docstore_service=docstore_service,
        reranking_service=reranking_service,
        table_qa_service=table_qa,
        multimodal_prompt_hints=MultimodalPromptHints(),
    )
    assembly = ApplicationPipelineAssembly(
        stages=post_recall_stage_ports_from_services(post_recall),
    )
    answer_generation_service = AnswerGenerationService()
    return RagRetrievalSubgraph(
        table_qa_service=table_qa,
        summary_recall_stage=summary,
        pipeline_assembly=assembly,
        post_recall_stage_services=post_recall,
        answer_generation_service=answer_generation_service,
        retrieval_settings_service=retrieval_settings_service,
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
        summary_recall_service=subgraph.summary_recall_stage,
        pipeline_assembly_service=subgraph.pipeline_assembly,
        query_log_emitter=emitter,
    )
    inspect_uc = InspectRagPipelineUseCase(retrieval=build_uc)
    preview_uc = PreviewSummaryRecallUseCase(summary_recall_service=subgraph.summary_recall_stage)
    generate_uc = GenerateAnswerFromPipelineUseCase(
        generation=subgraph.answer_generation_service,
    )
    ask_uc = AskQuestionUseCase(
        retrieval=build_uc,
        generation=subgraph.answer_generation_service,
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
    "post_recall_stage_ports_from_services",
]
