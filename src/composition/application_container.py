"""
Backend application container: explicit composition root for use cases and shared services.

This is the primary integration boundary for FastAPI and for headless callers. UI-specific code
should not need to import this module if it goes through :class:`~src.app.ragcraft_app.RAGCraftApp`
(legacy Streamlit façade), which delegates to a container built with the same
:class:`~src.composition.backend_composition.BackendComposition` instance where shared singletons
must align (for example the :class:`~src.domain.ports.QueryLogPort` implementation).
"""

from __future__ import annotations

from collections.abc import Callable
from functools import cached_property

from src.composition.backend_composition import BackendComposition, build_backend_composition


class BackendApplicationContainer:
    """
    Wires :class:`BackendComposition` services to application use cases.

    Dependencies are grouped by area through explicit properties and ``cached_property`` factories
    so import sites (for example ``apps.api.dependencies``) do not construct use cases ad hoc.
    """

    def __init__(
        self,
        *,
        backend: BackendComposition,
        invalidate_chain_key: Callable[[str], None],
    ) -> None:
        self._backend = backend
        self._invalidate_chain_key = invalidate_chain_key

    @property
    def backend(self) -> BackendComposition:
        return self._backend

    @property
    def auth_service(self):
        return self._backend.auth_service

    @property
    def project_service(self):
        return self._backend.project_service

    @property
    def ingestion_service(self):
        return self._backend.ingestion_service

    @property
    def vectorstore_service(self):
        return self._backend.vectorstore_service

    @property
    def evaluation_service(self):
        return self._backend.evaluation_service

    @property
    def chat_service(self):
        return self._backend.chat_service

    @property
    def docstore_service(self):
        return self._backend.docstore_service

    @property
    def reranking_service(self):
        return self._backend.reranking_service

    @property
    def qa_dataset_service(self):
        return self._backend.qa_dataset_service

    @property
    def qa_dataset_generation_service(self):
        return self._backend.qa_dataset_generation_service

    @property
    def project_settings_service(self):
        return self._backend.project_settings_service

    @property
    def query_log_service(self):
        return self._backend.query_log_service

    @property
    def rag_service(self):
        return self._backend.rag_service

    @property
    def retrieval_comparison_service(self):
        return self._backend.retrieval_comparison_service

    @property
    def project_settings_repository(self):
        """Port for retrieval preset persistence (same object as ``project_settings_service``)."""
        return self._backend.project_settings_service

    @property
    def retrieval_settings_service(self):
        return self._backend.retrieval_settings_service

    @cached_property
    def settings_get_effective_retrieval_use_case(self):
        from src.application.settings.use_cases.get_effective_retrieval_settings import (
            GetEffectiveRetrievalSettingsUseCase,
        )

        return GetEffectiveRetrievalSettingsUseCase(
            project_settings=self.project_settings_repository,
            retrieval_settings=self.retrieval_settings_service,
        )

    @cached_property
    def settings_update_project_retrieval_use_case(self):
        from src.application.settings.use_cases.update_project_retrieval_settings import (
            UpdateProjectRetrievalSettingsUseCase,
        )

        return UpdateProjectRetrievalSettingsUseCase(
            project_settings=self.project_settings_repository,
        )

    def invalidate_project_chain(self, user_id: str, project_id: str) -> None:
        from src.application.projects.use_cases.invalidate_project_chain_cache import (
            InvalidateProjectChainCacheUseCase,
        )

        InvalidateProjectChainCacheUseCase(
            project_service=self.project_service,
            invalidate_project_chain=self._invalidate_chain_key,
        ).execute(user_id=user_id, project_id=project_id)

    # --- Project use cases ---

    @cached_property
    def projects_list_projects_use_case(self):
        from src.application.projects.use_cases.list_projects import ListProjectsUseCase

        return ListProjectsUseCase(project_service=self.project_service)

    @cached_property
    def projects_create_project_use_case(self):
        from src.application.projects.use_cases.create_project import CreateProjectUseCase

        return CreateProjectUseCase(project_service=self.project_service)

    @cached_property
    def projects_list_project_documents_use_case(self):
        from src.application.projects.use_cases.list_project_documents import (
            ListProjectDocumentsUseCase,
        )

        return ListProjectDocumentsUseCase(project_service=self.project_service)

    # --- Chat use cases (via RAG service) ---

    @property
    def chat_ask_question_use_case(self):
        return self.rag_service.ask_question_use_case

    @property
    def chat_inspect_pipeline_use_case(self):
        return self.rag_service.inspect_pipeline_use_case

    @property
    def chat_preview_summary_recall_use_case(self):
        return self.rag_service.preview_summary_recall_use_case

    # --- Ingestion use cases ---

    @cached_property
    def ingestion_ingest_uploaded_file_use_case(self):
        from src.application.ingestion.use_cases.ingest_uploaded_file import IngestUploadedFileUseCase

        return IngestUploadedFileUseCase(
            ingestion_service=self.ingestion_service,
            asset_repository=self.docstore_service,
            vector_index=self.vectorstore_service,
            invalidate_project_chain=self.invalidate_project_chain,
        )

    @cached_property
    def ingestion_reindex_document_use_case(self):
        from src.application.ingestion.use_cases.reindex_document import ReindexDocumentUseCase

        return ReindexDocumentUseCase(
            ingestion_service=self.ingestion_service,
            asset_repository=self.docstore_service,
            vector_index=self.vectorstore_service,
            invalidate_project_chain=self.invalidate_project_chain,
        )

    @cached_property
    def ingestion_delete_document_use_case(self):
        from src.application.ingestion.use_cases.delete_document import DeleteDocumentUseCase

        return DeleteDocumentUseCase(
            asset_repository=self.docstore_service,
            vector_index=self.vectorstore_service,
            invalidate_project_chain=self.invalidate_project_chain,
        )

    # --- Evaluation use cases ---

    @cached_property
    def evaluation_create_qa_dataset_entry_use_case(self):
        from src.application.evaluation.use_cases.create_qa_dataset_entry import (
            CreateQaDatasetEntryUseCase,
        )

        return CreateQaDatasetEntryUseCase(qa_dataset=self.qa_dataset_service)

    @cached_property
    def evaluation_list_qa_dataset_entries_use_case(self):
        from src.application.evaluation.use_cases.list_qa_dataset_entries import (
            ListQaDatasetEntriesUseCase,
        )

        return ListQaDatasetEntriesUseCase(qa_dataset=self.qa_dataset_service)

    @cached_property
    def evaluation_run_manual_evaluation_use_case(self):
        from src.application.evaluation.use_cases.run_manual_evaluation import RunManualEvaluationUseCase

        return RunManualEvaluationUseCase(
            project_service=self.project_service,
            rag_service=self.rag_service,
            evaluation_service=self.evaluation_service,
        )

    @cached_property
    def evaluation_run_gold_qa_dataset_evaluation_use_case(self):
        from src.application.evaluation.use_cases.run_gold_qa_dataset_evaluation import (
            RunGoldQaDatasetEvaluationUseCase,
        )

        return RunGoldQaDatasetEvaluationUseCase(
            list_qa_dataset_entries=self.evaluation_list_qa_dataset_entries_use_case,
            project_service=self.project_service,
            rag_service=self.rag_service,
            evaluation_service=self.evaluation_service,
        )

    @cached_property
    def evaluation_update_qa_dataset_entry_use_case(self):
        from src.application.evaluation.use_cases.update_qa_dataset_entry import (
            UpdateQaDatasetEntryUseCase,
        )

        return UpdateQaDatasetEntryUseCase(qa_dataset=self.qa_dataset_service)

    @cached_property
    def evaluation_delete_qa_dataset_entry_use_case(self):
        from src.application.evaluation.use_cases.delete_qa_dataset_entry import (
            DeleteQaDatasetEntryUseCase,
        )

        return DeleteQaDatasetEntryUseCase(qa_dataset=self.qa_dataset_service)

    @cached_property
    def evaluation_generate_qa_dataset_use_case(self):
        from src.application.evaluation.use_cases.generate_qa_dataset import GenerateQaDatasetUseCase

        return GenerateQaDatasetUseCase(
            qa_dataset=self.qa_dataset_service,
            qa_dataset_generation_service=self.qa_dataset_generation_service,
        )

    @cached_property
    def evaluation_build_benchmark_export_artifacts_use_case(self):
        from src.application.evaluation.use_cases.build_benchmark_export_artifacts import (
            BuildBenchmarkExportArtifactsUseCase,
        )

        return BuildBenchmarkExportArtifactsUseCase()

    # --- Retrieval logs (evaluation module) ---

    @cached_property
    def evaluation_list_retrieval_query_logs_use_case(self):
        from src.application.evaluation.use_cases.list_retrieval_query_logs import (
            ListRetrievalQueryLogsUseCase,
        )

        return ListRetrievalQueryLogsUseCase(query_log=self.query_log_service)

    @property
    def retrieval_analytics_list_query_logs_use_case(self):
        """Backward-compatible alias for :attr:`evaluation_list_retrieval_query_logs_use_case`."""
        return self.evaluation_list_retrieval_query_logs_use_case


def build_backend_application_container(
    *,
    backend: BackendComposition | None = None,
    invalidate_chain_key: Callable[[str], None],
) -> BackendApplicationContainer:
    """Construct a container; when ``backend`` is omitted, a new composition graph is built."""
    resolved_backend = backend if backend is not None else build_backend_composition()
    return BackendApplicationContainer(
        backend=resolved_backend,
        invalidate_chain_key=invalidate_chain_key,
    )


__all__ = [
    "BackendApplicationContainer",
    "build_backend_application_container",
]
