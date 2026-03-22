"""
FastAPI dependency providers (transport layer).

**Composition root:** :func:`get_backend_application_container` returns a cached
:class:`~src.composition.application_container.BackendApplicationContainer` built via
:func:`~src.composition.build_backend`. Service-level graph alone is
:class:`~src.composition.backend_composition.BackendComposition` via
:func:`~src.composition.build_backend_composition`.

FastAPI does not reference ``src.app`` or the legacy interactive UI shell. Retrieval handle eviction uses
:class:`~src.infrastructure.caching.process_project_chain_cache.ProcessProjectChainCache`.

Importing this module loads the composition package (typed service + use-case graph) so dependency
signatures stay explicit; the container **instance** is still created lazily on first
:func:`get_backend_application_container` call (``lru_cache``).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header, HTTPException

from src.application.chat.use_cases.ask_question import AskQuestionUseCase
from src.application.chat.use_cases.inspect_rag_pipeline import InspectRagPipelineUseCase
from src.application.chat.use_cases.preview_summary_recall import PreviewSummaryRecallUseCase
from src.application.evaluation.use_cases.build_benchmark_export_artifacts import (
    BuildBenchmarkExportArtifactsUseCase,
)
from src.application.evaluation.use_cases.create_qa_dataset_entry import CreateQaDatasetEntryUseCase
from src.application.evaluation.use_cases.delete_qa_dataset_entry import DeleteQaDatasetEntryUseCase
from src.application.evaluation.use_cases.generate_qa_dataset import GenerateQaDatasetUseCase
from src.application.evaluation.use_cases.list_qa_dataset_entries import ListQaDatasetEntriesUseCase
from src.application.evaluation.use_cases.list_retrieval_query_logs import ListRetrievalQueryLogsUseCase
from src.application.evaluation.use_cases.run_gold_qa_dataset_evaluation import (
    RunGoldQaDatasetEvaluationUseCase,
)
from src.application.evaluation.use_cases.run_manual_evaluation import RunManualEvaluationUseCase
from src.application.evaluation.use_cases.update_qa_dataset_entry import UpdateQaDatasetEntryUseCase
from src.application.ingestion.use_cases.delete_document import DeleteDocumentUseCase
from src.application.ingestion.use_cases.ingest_uploaded_file import IngestUploadedFileUseCase
from src.application.ingestion.use_cases.reindex_document import ReindexDocumentUseCase
from src.application.projects.use_cases.create_project import CreateProjectUseCase
from src.application.projects.use_cases.list_project_documents import ListProjectDocumentsUseCase
from src.application.projects.use_cases.list_projects import ListProjectsUseCase
from src.application.settings.use_cases.get_effective_retrieval_settings import (
    GetEffectiveRetrievalSettingsUseCase,
)
from src.application.settings.use_cases.update_project_retrieval_settings import (
    UpdateProjectRetrievalSettingsUseCase,
)
from src.auth.user_repository import UserRepository
from src.composition.application_container import BackendApplicationContainer
from src.services.docstore_service import DocStoreService
from src.services.project_service import ProjectService
from src.services.project_settings_service import ProjectSettingsService
from src.services.rag_service import RAGService
from src.services.retrieval_comparison_service import RetrievalComparisonService


@lru_cache(maxsize=1)
def get_backend_application_container() -> BackendApplicationContainer:
    from src.composition import build_backend
    from src.infrastructure.caching.process_project_chain_cache import (
        get_default_process_project_chain_cache,
    )

    process_chain_cache = get_default_process_project_chain_cache()
    return build_backend(invalidate_chain_key=process_chain_cache.drop)


BackendContainerDep = Annotated[BackendApplicationContainer, Depends(get_backend_application_container)]


def get_project_service(container: BackendContainerDep) -> ProjectService:
    return container.project_service


def get_request_user_id(
    x_user_id: Annotated[
        str | None,
        Header(
            alias="X-User-Id",
            description=(
                "Required workspace user id. Extension point: replace with a verified principal "
                "from OAuth/JWT without changing route paths."
            ),
        ),
    ] = None,
) -> str:
    if x_user_id is None or not str(x_user_id).strip():
        raise HTTPException(
            status_code=400,
            detail="Missing or empty X-User-Id header.",
        )
    return str(x_user_id).strip()


def get_list_projects_use_case(container: BackendContainerDep) -> ListProjectsUseCase:
    return container.projects_list_projects_use_case


def get_create_project_use_case(container: BackendContainerDep) -> CreateProjectUseCase:
    return container.projects_create_project_use_case


def get_get_effective_retrieval_settings_use_case(
    container: BackendContainerDep,
) -> GetEffectiveRetrievalSettingsUseCase:
    return container.settings_get_effective_retrieval_use_case


def get_update_project_retrieval_settings_use_case(
    container: BackendContainerDep,
) -> UpdateProjectRetrievalSettingsUseCase:
    return container.settings_update_project_retrieval_use_case


def get_list_project_documents_use_case(container: BackendContainerDep) -> ListProjectDocumentsUseCase:
    return container.projects_list_project_documents_use_case


def get_rag_service(container: BackendContainerDep) -> RAGService:
    return container.rag_service


def get_ask_question_use_case(container: BackendContainerDep) -> AskQuestionUseCase:
    return container.chat_ask_question_use_case


def get_inspect_pipeline_use_case(container: BackendContainerDep) -> InspectRagPipelineUseCase:
    return container.chat_inspect_pipeline_use_case


def get_preview_summary_recall_use_case(container: BackendContainerDep) -> PreviewSummaryRecallUseCase:
    return container.chat_preview_summary_recall_use_case


def get_create_qa_dataset_entry_use_case(container: BackendContainerDep) -> CreateQaDatasetEntryUseCase:
    return container.evaluation_create_qa_dataset_entry_use_case


def get_list_qa_dataset_entries_use_case(container: BackendContainerDep) -> ListQaDatasetEntriesUseCase:
    return container.evaluation_list_qa_dataset_entries_use_case


def get_build_benchmark_export_artifacts_use_case(
    container: BackendContainerDep,
) -> BuildBenchmarkExportArtifactsUseCase:
    return container.evaluation_build_benchmark_export_artifacts_use_case


def get_run_manual_evaluation_use_case(container: BackendContainerDep) -> RunManualEvaluationUseCase:
    return container.evaluation_run_manual_evaluation_use_case


def get_run_gold_qa_dataset_evaluation_use_case(
    container: BackendContainerDep,
) -> RunGoldQaDatasetEvaluationUseCase:
    return container.evaluation_run_gold_qa_dataset_evaluation_use_case


def get_update_qa_dataset_entry_use_case(container: BackendContainerDep) -> UpdateQaDatasetEntryUseCase:
    return container.evaluation_update_qa_dataset_entry_use_case


def get_delete_qa_dataset_entry_use_case(container: BackendContainerDep) -> DeleteQaDatasetEntryUseCase:
    return container.evaluation_delete_qa_dataset_entry_use_case


def get_generate_qa_dataset_use_case(container: BackendContainerDep) -> GenerateQaDatasetUseCase:
    return container.evaluation_generate_qa_dataset_use_case


def get_list_retrieval_query_logs_use_case(
    container: BackendContainerDep,
) -> ListRetrievalQueryLogsUseCase:
    return container.evaluation_list_retrieval_query_logs_use_case


def get_ingest_uploaded_file_use_case(container: BackendContainerDep) -> IngestUploadedFileUseCase:
    return container.ingestion_ingest_uploaded_file_use_case


def get_reindex_document_use_case(container: BackendContainerDep) -> ReindexDocumentUseCase:
    return container.ingestion_reindex_document_use_case


def get_delete_document_use_case(container: BackendContainerDep) -> DeleteDocumentUseCase:
    return container.ingestion_delete_document_use_case


def get_docstore_service(container: BackendContainerDep) -> DocStoreService:
    return container.docstore_service


def get_project_settings_service(container: BackendContainerDep) -> ProjectSettingsService:
    return container.project_settings_service


def get_retrieval_comparison_service(container: BackendContainerDep) -> RetrievalComparisonService:
    return container.retrieval_comparison_service


def ensure_auth_database() -> bool:
    """Create SQLite app tables if missing (users router dependency)."""
    from src.infrastructure.persistence.db import init_app_db

    init_app_db()
    return True


def get_user_repository(
    _: Annotated[bool, Depends(ensure_auth_database)],
) -> UserRepository:
    return UserRepository()
