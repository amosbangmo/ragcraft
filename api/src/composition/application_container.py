"""
Application composition root: wires technical services from
:class:`~composition.backend_composition.BackendComposition` into use cases for FastAPI,
headless callers, and the Streamlit façade.

Use :func:`build_backend_composition` to build the service graph (pass ``chat_transcript``), then
:func:`build_backend` or :func:`build_backend_application_container` to attach use cases and the chain
invalidation hook.

**Orchestration inventory (this module):**

- Lazy construction of use cases and injection of ports (e.g. memoized
  :attr:`~composition.application_container.BackendApplicationContainer.chat_rag_use_cases` from
  :mod:`composition.chat_rag_wiring`). There is no ``rag_service`` façade on the container.
- Single allowed direct ``execute`` call: :meth:`BackendApplicationContainer.invalidate_project_chain`
  delegates to :class:`~application.use_cases.projects.invalidate_project_chain_cache.InvalidateProjectChainCacheUseCase`
  (cache lifecycle, not RAG sequencing).

**Target ownership:** no multi-step RAG or evaluation flow logic here — only ``UseCase(...)`` wiring and
passing references (e.g. ``inspect_pipeline`` into evaluation use cases). Compare-retrieval and gold-QA
orchestration live in their respective use cases under ``src/application/use_cases``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from functools import cached_property
from typing import TYPE_CHECKING

from application.services.retrieval_settings_tuner import RetrievalSettingsTuner
from composition.backend_composition import BackendComposition
from domain.common.ports.access_token_issuer_port import AccessTokenIssuerPort
from domain.common.ports.authentication_port import AuthenticationPort
from domain.common.ports.chat_transcript_port import ChatTranscriptPort
from domain.common.shared.project_settings_repository_port import ProjectSettingsRepositoryPort
from infrastructure.auth.auth_service import AuthService
from infrastructure.evaluation.evaluation_service import EvaluationService
from infrastructure.evaluation.qa_dataset_generation_service import (
    QADatasetGenerationService,
)
from infrastructure.evaluation.qa_dataset_service import QADatasetService
from infrastructure.observability.query_log_service import QueryLogService
from infrastructure.persistence.project_service import ProjectService
from infrastructure.rag.docstore_service import DocStoreService
from infrastructure.rag.reranking_service import RerankingService

if TYPE_CHECKING:
    from application.orchestration.evaluation.build_benchmark_export_artifacts import (
        BuildBenchmarkExportArtifactsUseCase,
    )
    from application.use_cases.chat.ask_question import AskQuestionUseCase
    from application.use_cases.chat.build_rag_pipeline import BuildRagPipelineUseCase
    from application.use_cases.chat.generate_answer_from_pipeline import (
        GenerateAnswerFromPipelineUseCase,
    )
    from application.use_cases.chat.inspect_rag_pipeline import InspectRagPipelineUseCase
    from application.use_cases.chat.preview_summary_recall import PreviewSummaryRecallUseCase
    from application.use_cases.evaluation.create_qa_dataset_entry import (
        CreateQaDatasetEntryUseCase,
    )
    from application.use_cases.evaluation.delete_qa_dataset_entry import (
        DeleteQaDatasetEntryUseCase,
    )
    from application.use_cases.evaluation.generate_qa_dataset import GenerateQaDatasetUseCase
    from application.use_cases.evaluation.list_qa_dataset_entries import (
        ListQaDatasetEntriesUseCase,
    )
    from application.use_cases.evaluation.list_retrieval_query_logs import (
        ListRetrievalQueryLogsUseCase,
    )
    from application.use_cases.evaluation.run_gold_qa_dataset_evaluation import (
        RunGoldQaDatasetEvaluationUseCase,
    )
    from application.use_cases.evaluation.run_manual_evaluation import (
        RunManualEvaluationUseCase,
    )
    from application.use_cases.evaluation.update_qa_dataset_entry import (
        UpdateQaDatasetEntryUseCase,
    )
    from application.use_cases.ingestion.delete_document import DeleteDocumentUseCase
    from application.use_cases.ingestion.ingest_uploaded_file import IngestUploadedFileUseCase
    from application.use_cases.ingestion.reindex_document import ReindexDocumentUseCase
    from application.use_cases.projects.create_project import CreateProjectUseCase
    from application.use_cases.projects.list_project_documents import (
        ListProjectDocumentsUseCase,
    )
    from application.use_cases.projects.list_projects import ListProjectsUseCase
    from application.use_cases.retrieval.compare_retrieval_modes import (
        CompareRetrievalModesUseCase,
    )
    from application.use_cases.settings.get_effective_retrieval_settings import (
        GetEffectiveRetrievalSettingsUseCase,
    )
    from application.use_cases.settings.update_project_retrieval_settings import (
        UpdateProjectRetrievalSettingsUseCase,
    )
    from composition.chat_rag_wiring import ChatRagUseCases
    from infrastructure.rag.ingestion_service import IngestionService
    from infrastructure.rag.vectorstore_service import VectorStoreService


@dataclass
class BackendApplicationContainer:
    """
    Typed façade over the service graph with lazily memoized use-case instances.

    FastAPI should resolve dependencies from this type (via ``interfaces.http.dependencies``), not by
    constructing services ad hoc.
    """

    backend: BackendComposition
    # Composition-boundary hook: evicts process-scoped handles (``ProcessProjectChainCache.drop`` for
    # FastAPI). Streamlit entrypoints may wrap the same hook to also clear session-scoped caches.
    _invalidate_chain_key: Callable[[str], None] = field(repr=False)

    @property
    def auth_service(self) -> AuthService:
        return self.backend.auth_service

    @property
    def authentication(self) -> AuthenticationPort:
        return self.backend.bearer_token_auth

    @property
    def access_token_issuer(self) -> AccessTokenIssuerPort:
        return self.backend.bearer_token_auth

    @property
    def project_service(self) -> ProjectService:
        return self.backend.project_service

    @property
    def ingestion_service(self) -> IngestionService:
        return self.backend.ingestion_service

    @property
    def vectorstore_service(self) -> VectorStoreService:
        return self.backend.vectorstore_service

    @property
    def evaluation_service(self) -> EvaluationService:
        return self.backend.evaluation_service

    @property
    def chat_transcript(self) -> ChatTranscriptPort:
        return self.backend.chat_transcript

    @property
    def docstore_service(self) -> DocStoreService:
        return self.backend.docstore_service

    @property
    def reranking_service(self) -> RerankingService:
        return self.backend.reranking_service

    @property
    def qa_dataset_service(self) -> QADatasetService:
        return self.backend.qa_dataset_service

    @property
    def qa_dataset_generation_service(self) -> QADatasetGenerationService:
        return self.backend.qa_dataset_generation_service

    @property
    def query_log_service(self) -> QueryLogService:
        return self.backend.query_log_service

    @property
    def project_settings_repository(self) -> ProjectSettingsRepositoryPort:
        return self.backend.project_settings_repository

    @property
    def retrieval_settings_tuner(self) -> RetrievalSettingsTuner:
        return self.backend.retrieval_settings_tuner

    @cached_property
    def settings_get_effective_retrieval_use_case(self) -> GetEffectiveRetrievalSettingsUseCase:
        from application.use_cases.settings.get_effective_retrieval_settings import (
            GetEffectiveRetrievalSettingsUseCase,
        )

        return GetEffectiveRetrievalSettingsUseCase(
            project_settings=self.project_settings_repository,
            retrieval_settings=self.retrieval_settings_tuner,
        )

    @cached_property
    def settings_update_project_retrieval_use_case(self) -> UpdateProjectRetrievalSettingsUseCase:
        from application.use_cases.settings.update_project_retrieval_settings import (
            UpdateProjectRetrievalSettingsUseCase,
        )

        return UpdateProjectRetrievalSettingsUseCase(
            project_settings=self.project_settings_repository,
        )

    @cached_property
    def projects_resolve_project_use_case(self):
        from application.use_cases.projects.resolve_project import ResolveProjectUseCase

        return ResolveProjectUseCase(project_service=self.project_service)

    @cached_property
    def projects_invalidate_project_chain_cache_use_case(self):
        from application.use_cases.projects.invalidate_project_chain_cache import (
            InvalidateProjectChainCacheUseCase,
        )

        return InvalidateProjectChainCacheUseCase(
            resolve_project=self.projects_resolve_project_use_case,
            invalidate_project_chain=self._invalidate_chain_key,
        )

    def invalidate_project_chain(self, user_id: str, project_id: str) -> None:
        self.projects_invalidate_project_chain_cache_use_case.execute(
            user_id=user_id, project_id=project_id
        )

    @cached_property
    def projects_list_projects_use_case(self) -> ListProjectsUseCase:
        from application.use_cases.projects.list_projects import ListProjectsUseCase

        return ListProjectsUseCase(project_service=self.project_service)

    @cached_property
    def projects_create_project_use_case(self) -> CreateProjectUseCase:
        from application.use_cases.projects.create_project import CreateProjectUseCase

        return CreateProjectUseCase(project_service=self.project_service)

    @cached_property
    def projects_list_project_documents_use_case(self) -> ListProjectDocumentsUseCase:
        from application.use_cases.projects.list_project_documents import (
            ListProjectDocumentsUseCase,
        )

        return ListProjectDocumentsUseCase(project_service=self.project_service)

    @cached_property
    def projects_get_project_document_details_use_case(self):
        from application.use_cases.projects.get_project_document_details import (
            GetProjectDocumentDetailsUseCase,
        )

        return GetProjectDocumentDetailsUseCase(
            resolve_project=self.projects_resolve_project_use_case,
            asset_repository=self.docstore_service,
        )

    @cached_property
    def projects_list_document_assets_for_source_use_case(self):
        from application.use_cases.projects.list_document_assets_for_source import (
            ListDocumentAssetsForSourceUseCase,
        )

        return ListDocumentAssetsForSourceUseCase(asset_repository=self.docstore_service)

    @cached_property
    def projects_get_retrieval_preset_label_use_case(self):
        from application.use_cases.projects.get_project_retrieval_preset_label import (
            GetProjectRetrievalPresetLabelUseCase,
        )

        return GetProjectRetrievalPresetLabelUseCase(
            project_settings=self.project_settings_repository
        )

    @cached_property
    def chat_rag_use_cases(self) -> ChatRagUseCases:
        """
        Memoized chat/RAG use-case bundle (same wiring as :mod:`composition.chat_rag_wiring`).

        Exposed explicitly so callers use application use cases — not a legacy ``RAGService`` façade.
        """
        from composition.chat_rag_wiring import (
            build_chat_rag_use_cases,
            build_rag_retrieval_subgraph,
        )

        subgraph = build_rag_retrieval_subgraph(
            vectorstore_service=self.backend.vectorstore_service,
            docstore_service=self.backend.docstore_service,
            reranking_service=self.backend.reranking_service,
            retrieval_settings_tuner=self.backend.retrieval_settings_tuner,
        )
        return build_chat_rag_use_cases(subgraph, query_log=self.query_log_service)

    @property
    def chat_ask_question_use_case(self) -> AskQuestionUseCase:
        return self.chat_rag_use_cases.ask_question

    @property
    def chat_inspect_pipeline_use_case(self) -> InspectRagPipelineUseCase:
        return self.chat_rag_use_cases.inspect_rag_pipeline

    @property
    def chat_preview_summary_recall_use_case(self) -> PreviewSummaryRecallUseCase:
        return self.chat_rag_use_cases.preview_summary_recall

    @property
    def chat_build_rag_pipeline_use_case(self) -> BuildRagPipelineUseCase:
        return self.chat_rag_use_cases.build_rag_pipeline

    @property
    def chat_generate_answer_from_pipeline_use_case(self) -> GenerateAnswerFromPipelineUseCase:
        return self.chat_rag_use_cases.generate_answer_from_pipeline

    @cached_property
    def chat_compare_retrieval_modes_use_case(self) -> CompareRetrievalModesUseCase:
        from application.use_cases.retrieval.compare_retrieval_modes import (
            CompareRetrievalModesUseCase,
        )

        return CompareRetrievalModesUseCase(
            resolve_project=self.projects_resolve_project_use_case,
            inspect_pipeline=self.chat_inspect_pipeline_use_case,
        )

    @cached_property
    def ingestion_ingest_uploaded_file_use_case(self) -> IngestUploadedFileUseCase:
        from application.use_cases.ingestion.ingest_uploaded_file import (
            IngestUploadedFileUseCase,
        )

        return IngestUploadedFileUseCase(
            ingestion_service=self.ingestion_service,
            asset_repository=self.docstore_service,
            vector_index=self.vectorstore_service,
            invalidate_project_chain=self.invalidate_project_chain,
        )

    @cached_property
    def ingestion_reindex_document_use_case(self) -> ReindexDocumentUseCase:
        from application.use_cases.ingestion.reindex_document import ReindexDocumentUseCase

        return ReindexDocumentUseCase(
            ingestion_service=self.ingestion_service,
            asset_repository=self.docstore_service,
            vector_index=self.vectorstore_service,
            invalidate_project_chain=self.invalidate_project_chain,
        )

    @cached_property
    def ingestion_delete_document_use_case(self) -> DeleteDocumentUseCase:
        from application.use_cases.ingestion.delete_document import DeleteDocumentUseCase

        return DeleteDocumentUseCase(
            asset_repository=self.docstore_service,
            vector_index=self.vectorstore_service,
            invalidate_project_chain=self.invalidate_project_chain,
        )

    @cached_property
    def evaluation_create_qa_dataset_entry_use_case(self) -> CreateQaDatasetEntryUseCase:
        from application.use_cases.evaluation.create_qa_dataset_entry import (
            CreateQaDatasetEntryUseCase,
        )

        return CreateQaDatasetEntryUseCase(qa_dataset=self.qa_dataset_service)

    @cached_property
    def evaluation_list_qa_dataset_entries_use_case(self) -> ListQaDatasetEntriesUseCase:
        from application.use_cases.evaluation.list_qa_dataset_entries import (
            ListQaDatasetEntriesUseCase,
        )

        return ListQaDatasetEntriesUseCase(qa_dataset=self.qa_dataset_service)

    @cached_property
    def evaluation_run_manual_evaluation_use_case(self) -> RunManualEvaluationUseCase:
        from application.use_cases.evaluation.run_manual_evaluation import (
            RunManualEvaluationUseCase,
        )

        return RunManualEvaluationUseCase(
            project_service=self.project_service,
            inspect_pipeline=self.chat_inspect_pipeline_use_case,
            generate_answer_from_pipeline=self.chat_generate_answer_from_pipeline_use_case,
            manual_evaluation=self.evaluation_service,
        )

    @cached_property
    def evaluation_run_gold_qa_dataset_evaluation_use_case(
        self,
    ) -> RunGoldQaDatasetEvaluationUseCase:
        from application.use_cases.evaluation.run_gold_qa_dataset_evaluation import (
            RunGoldQaDatasetEvaluationUseCase,
        )

        return RunGoldQaDatasetEvaluationUseCase(
            list_qa_dataset_entries=self.evaluation_list_qa_dataset_entries_use_case,
            project_service=self.project_service,
            inspect_pipeline=self.chat_inspect_pipeline_use_case,
            generate_answer_from_pipeline=self.chat_generate_answer_from_pipeline_use_case,
            gold_benchmark=self.evaluation_service,
        )

    @cached_property
    def evaluation_update_qa_dataset_entry_use_case(self) -> UpdateQaDatasetEntryUseCase:
        from application.use_cases.evaluation.update_qa_dataset_entry import (
            UpdateQaDatasetEntryUseCase,
        )

        return UpdateQaDatasetEntryUseCase(qa_dataset=self.qa_dataset_service)

    @cached_property
    def evaluation_delete_qa_dataset_entry_use_case(self) -> DeleteQaDatasetEntryUseCase:
        from application.use_cases.evaluation.delete_qa_dataset_entry import (
            DeleteQaDatasetEntryUseCase,
        )

        return DeleteQaDatasetEntryUseCase(qa_dataset=self.qa_dataset_service)

    @cached_property
    def evaluation_generate_qa_dataset_use_case(self) -> GenerateQaDatasetUseCase:
        from application.use_cases.evaluation.generate_qa_dataset import (
            GenerateQaDatasetUseCase,
        )

        return GenerateQaDatasetUseCase(
            qa_dataset=self.qa_dataset_service,
            qa_dataset_generation_service=self.qa_dataset_generation_service,
        )

    @cached_property
    def evaluation_build_benchmark_export_artifacts_use_case(
        self,
    ) -> BuildBenchmarkExportArtifactsUseCase:
        from application.orchestration.evaluation.build_benchmark_export_artifacts import (
            BuildBenchmarkExportArtifactsUseCase,
        )

        return BuildBenchmarkExportArtifactsUseCase()

    @cached_property
    def evaluation_list_retrieval_query_logs_use_case(self) -> ListRetrievalQueryLogsUseCase:
        from application.use_cases.evaluation.list_retrieval_query_logs import (
            ListRetrievalQueryLogsUseCase,
        )

        return ListRetrievalQueryLogsUseCase(query_log=self.query_log_service)

    @property
    def retrieval_analytics_list_query_logs_use_case(self) -> ListRetrievalQueryLogsUseCase:
        return self.evaluation_list_retrieval_query_logs_use_case


def build_backend_application_container(
    *,
    backend: BackendComposition,
    invalidate_chain_key: Callable[[str], None],
) -> BackendApplicationContainer:
    """Attach use-case wiring to a built service graph."""
    return BackendApplicationContainer(backend=backend, _invalidate_chain_key=invalidate_chain_key)


def build_backend(
    *,
    invalidate_chain_key: Callable[[str], None],
    backend: BackendComposition,
) -> BackendApplicationContainer:
    """
    Full backend graph (services + application use cases).

    Build :class:`~composition.backend_composition.BackendComposition` first (with the desired
    ``chat_transcript``), then pass it here.
    """
    return build_backend_application_container(
        backend=backend,
        invalidate_chain_key=invalidate_chain_key,
    )


__all__ = [
    "BackendApplicationContainer",
    "build_backend",
    "build_backend_application_container",
]
