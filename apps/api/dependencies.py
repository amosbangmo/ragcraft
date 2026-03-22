"""
FastAPI dependency providers.

**Primary entrypoint:** :func:`get_backend_application_container` — process-wide
:class:`~src.composition.application_container.BackendApplicationContainer` from
:func:`~src.composition.build_backend` (composition root: services + use cases).

FastAPI wiring does **not** import the legacy UI façade in ``src.app`` or UI entrypoints; the HTTP
API’s composition graph is independent of the desktop UI process.
Project-level retrieval handle eviction uses
:class:`~src.infrastructure.caching.process_project_chain_cache.ProcessProjectChainCache` only.

The composition build stays inside a cached getter so ``import apps.api.dependencies`` does not load
FAISS, LangChain, or UI session chain state until a route resolves a dependency. Service return
types below are explicit where imports stay cheap;
chat and evaluation use cases that sit behind :class:`~src.services.rag_service.RAGService` remain
``Any`` at the annotation layer to avoid eager heavy imports.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Any

from fastapi import Depends, Header, HTTPException

from src.auth.user_repository import UserRepository
from src.services.docstore_service import DocStoreService
from src.services.project_service import ProjectService
from src.services.project_settings_service import ProjectSettingsService
from src.services.retrieval_comparison_service import RetrievalComparisonService


@lru_cache(maxsize=1)
def get_backend_application_container() -> Any:
    from src.composition import build_backend
    from src.infrastructure.caching.process_project_chain_cache import (
        get_default_process_project_chain_cache,
    )

    process_chain_cache = get_default_process_project_chain_cache()
    return build_backend(invalidate_chain_key=process_chain_cache.drop)


BackendContainerDep = Annotated[Any, Depends(get_backend_application_container)]


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


def get_list_projects_use_case(container: BackendContainerDep) -> Any:
    return container.projects_list_projects_use_case


def get_create_project_use_case(container: BackendContainerDep) -> Any:
    return container.projects_create_project_use_case


def get_get_effective_retrieval_settings_use_case(container: BackendContainerDep) -> Any:
    return container.settings_get_effective_retrieval_use_case


def get_update_project_retrieval_settings_use_case(container: BackendContainerDep) -> Any:
    return container.settings_update_project_retrieval_use_case


def get_list_project_documents_use_case(container: BackendContainerDep) -> Any:
    return container.projects_list_project_documents_use_case


def get_rag_service(container: BackendContainerDep) -> Any:
    return container.rag_service


def get_ask_question_use_case(container: BackendContainerDep) -> Any:
    return container.chat_ask_question_use_case


def get_inspect_pipeline_use_case(container: BackendContainerDep) -> Any:
    return container.chat_inspect_pipeline_use_case


def get_preview_summary_recall_use_case(container: BackendContainerDep) -> Any:
    return container.chat_preview_summary_recall_use_case


def get_create_qa_dataset_entry_use_case(container: BackendContainerDep) -> Any:
    return container.evaluation_create_qa_dataset_entry_use_case


def get_list_qa_dataset_entries_use_case(container: BackendContainerDep) -> Any:
    return container.evaluation_list_qa_dataset_entries_use_case


def get_build_benchmark_export_artifacts_use_case(container: BackendContainerDep) -> Any:
    return container.evaluation_build_benchmark_export_artifacts_use_case


def get_run_manual_evaluation_use_case(container: BackendContainerDep) -> Any:
    return container.evaluation_run_manual_evaluation_use_case


def get_run_gold_qa_dataset_evaluation_use_case(container: BackendContainerDep) -> Any:
    return container.evaluation_run_gold_qa_dataset_evaluation_use_case


def get_update_qa_dataset_entry_use_case(container: BackendContainerDep) -> Any:
    return container.evaluation_update_qa_dataset_entry_use_case


def get_delete_qa_dataset_entry_use_case(container: BackendContainerDep) -> Any:
    return container.evaluation_delete_qa_dataset_entry_use_case


def get_generate_qa_dataset_use_case(container: BackendContainerDep) -> Any:
    return container.evaluation_generate_qa_dataset_use_case


def get_list_retrieval_query_logs_use_case(container: BackendContainerDep) -> Any:
    return container.evaluation_list_retrieval_query_logs_use_case


def get_ingest_uploaded_file_use_case(container: BackendContainerDep) -> Any:
    return container.ingestion_ingest_uploaded_file_use_case


def get_reindex_document_use_case(container: BackendContainerDep) -> Any:
    return container.ingestion_reindex_document_use_case


def get_delete_document_use_case(container: BackendContainerDep) -> Any:
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
