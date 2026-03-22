"""
FastAPI dependency providers.

**Primary entrypoint:** :func:`get_backend_application_container` — process-wide
:class:`~src.composition.backend_composition.BackendComposition` plus named use cases and services.

:class:`~src.app.ragcraft_app.RAGCraftApp` is used only by Streamlit in-process mode
(``InProcessBackendClient``); FastAPI routes must depend on this module's container getters, not the façade.

Use-case imports stay deferred inside getters where needed so ``import apps.api.dependencies`` does
not load FAISS / LangChain (keeps ``/health`` importable in minimal environments).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Any

from fastapi import Depends, Header, HTTPException

from src.services.project_service import ProjectService


@lru_cache(maxsize=1)
def get_backend_composition() -> Any:
    from src.composition import build_backend_composition

    return build_backend_composition()


@lru_cache(maxsize=1)
def get_backend_application_container() -> Any:
    from src.composition import build_backend_application_container
    from src.core.chain_state import invalidate_project_chain as invalidate_chain_key

    return build_backend_application_container(
        backend=get_backend_composition(),
        invalidate_chain_key=invalidate_chain_key,
    )


def get_project_service(
    container: Annotated[Any, Depends(get_backend_application_container)],
) -> ProjectService:
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


def get_list_projects_use_case(
    container: Annotated[Any, Depends(get_backend_application_container)],
) -> Any:
    return container.projects_list_projects_use_case


def get_create_project_use_case(
    container: Annotated[Any, Depends(get_backend_application_container)],
) -> Any:
    return container.projects_create_project_use_case


def get_get_effective_retrieval_settings_use_case(
    container: Annotated[Any, Depends(get_backend_application_container)],
) -> Any:
    return container.settings_get_effective_retrieval_use_case


def get_update_project_retrieval_settings_use_case(
    container: Annotated[Any, Depends(get_backend_application_container)],
) -> Any:
    return container.settings_update_project_retrieval_use_case


def get_list_project_documents_use_case(
    container: Annotated[Any, Depends(get_backend_application_container)],
) -> Any:
    return container.projects_list_project_documents_use_case


def get_rag_service(
    container: Annotated[Any, Depends(get_backend_application_container)],
) -> Any:
    return container.rag_service


def get_ask_question_use_case(
    container: Annotated[Any, Depends(get_backend_application_container)],
) -> Any:
    return container.chat_ask_question_use_case


def get_inspect_pipeline_use_case(
    container: Annotated[Any, Depends(get_backend_application_container)],
) -> Any:
    return container.chat_inspect_pipeline_use_case


def get_preview_summary_recall_use_case(
    container: Annotated[Any, Depends(get_backend_application_container)],
) -> Any:
    return container.chat_preview_summary_recall_use_case


def get_create_qa_dataset_entry_use_case(
    container: Annotated[Any, Depends(get_backend_application_container)],
) -> Any:
    return container.evaluation_create_qa_dataset_entry_use_case


def get_list_qa_dataset_entries_use_case(
    container: Annotated[Any, Depends(get_backend_application_container)],
) -> Any:
    return container.evaluation_list_qa_dataset_entries_use_case


def get_build_benchmark_export_artifacts_use_case(
    container: Annotated[Any, Depends(get_backend_application_container)],
) -> Any:
    return container.evaluation_build_benchmark_export_artifacts_use_case


def get_run_manual_evaluation_use_case(
    container: Annotated[Any, Depends(get_backend_application_container)],
) -> Any:
    return container.evaluation_run_manual_evaluation_use_case


def get_run_gold_qa_dataset_evaluation_use_case(
    container: Annotated[Any, Depends(get_backend_application_container)],
) -> Any:
    return container.evaluation_run_gold_qa_dataset_evaluation_use_case


def get_update_qa_dataset_entry_use_case(
    container: Annotated[Any, Depends(get_backend_application_container)],
) -> Any:
    return container.evaluation_update_qa_dataset_entry_use_case


def get_delete_qa_dataset_entry_use_case(
    container: Annotated[Any, Depends(get_backend_application_container)],
) -> Any:
    return container.evaluation_delete_qa_dataset_entry_use_case


def get_generate_qa_dataset_use_case(
    container: Annotated[Any, Depends(get_backend_application_container)],
) -> Any:
    return container.evaluation_generate_qa_dataset_use_case


def get_list_retrieval_query_logs_use_case(
    container: Annotated[Any, Depends(get_backend_application_container)],
) -> Any:
    return container.evaluation_list_retrieval_query_logs_use_case


def get_ingest_uploaded_file_use_case(
    container: Annotated[Any, Depends(get_backend_application_container)],
) -> Any:
    return container.ingestion_ingest_uploaded_file_use_case


def get_reindex_document_use_case(
    container: Annotated[Any, Depends(get_backend_application_container)],
) -> Any:
    return container.ingestion_reindex_document_use_case


def get_delete_document_use_case(
    container: Annotated[Any, Depends(get_backend_application_container)],
) -> Any:
    return container.ingestion_delete_document_use_case


def get_docstore_service(
    container: Annotated[Any, Depends(get_backend_application_container)],
) -> Any:
    return container.docstore_service


def get_project_settings_service(
    container: Annotated[Any, Depends(get_backend_application_container)],
) -> Any:
    return container.project_settings_service


def get_retrieval_comparison_service(
    container: Annotated[Any, Depends(get_backend_application_container)],
) -> Any:
    return container.retrieval_comparison_service


def ensure_auth_database() -> bool:
    """Create SQLite app tables if missing (users router dependency)."""
    from src.infrastructure.persistence.db import init_app_db

    init_app_db()
    return True


def get_user_repository(
    _: Annotated[bool, Depends(ensure_auth_database)],
) -> Any:
    from src.auth.user_repository import UserRepository

    return UserRepository()
