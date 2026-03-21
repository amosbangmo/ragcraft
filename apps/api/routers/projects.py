"""
Project and document management HTTP API.

All handlers depend on application use cases (or header-derived identity + use cases only).
File ingest uses multipart form field ``file``; see each route's OpenAPI description.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, UploadFile, status

from apps.api.dependencies import (
    get_create_project_use_case,
    get_delete_document_use_case,
    get_ingest_uploaded_file_use_case,
    get_list_project_documents_use_case,
    get_list_projects_use_case,
    get_project_service,
    get_reindex_document_use_case,
    get_request_user_id,
)
from apps.api.schemas.projects import (
    CreateProjectRequest,
    CreateProjectResponse,
    DeleteDocumentResponse,
    IngestDocumentResponse,
    ProjectDocumentsResponse,
    ProjectListResponse,
)
from apps.api.schemas.serialization import ingest_document_result_to_api_dict
from apps.api.upload_adapter import read_upload_for_ingestion
from src.application.ingestion.dtos import DeleteDocumentCommand, ReindexDocumentCommand
from src.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get(
    "",
    response_model=ProjectListResponse,
    summary="List projects for a user",
)
def get_projects(
    user_id: Annotated[str, Depends(get_request_user_id)],
    use_case: Annotated[Any, Depends(get_list_projects_use_case)],
) -> ProjectListResponse:
    """Returns sorted project ids under ``users/{X-User-Id}/projects``."""
    return ProjectListResponse(projects=use_case.execute(user_id))


@router.post(
    "",
    response_model=CreateProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or ensure a project",
)
def post_project(
    body: CreateProjectRequest,
    user_id: Annotated[str, Depends(get_request_user_id)],
    use_case: Annotated[Any, Depends(get_create_project_use_case)],
) -> CreateProjectResponse:
    """
    Creates the project directory if needed (idempotent).

    Example: ``POST /projects`` with header ``X-User-Id: alice`` and body
    ``{"project_id": "demo"}``.
    """
    use_case.execute(user_id, body.project_id)
    return CreateProjectResponse(project_id=body.project_id)


@router.get(
    "/{project_id}/documents",
    response_model=ProjectDocumentsResponse,
    summary="List documents in a project",
)
def get_project_documents(
    project_id: str,
    user_id: Annotated[str, Depends(get_request_user_id)],
    use_case: Annotated[Any, Depends(get_list_project_documents_use_case)],
) -> ProjectDocumentsResponse:
    """Sorted filenames at the project root (not including ``faiss_index`` or ``logs.json``)."""
    return ProjectDocumentsResponse(documents=use_case.execute(user_id, project_id))


@router.post(
    "/{project_id}/documents/ingest",
    response_model=IngestDocumentResponse,
    summary="Ingest an uploaded document",
    responses={
        502: {"description": "LLM or upstream model failure during summarization"},
        503: {"description": "Vector store, doc store, or extraction failure"},
    },
)
async def post_document_ingest(
    project_id: str,
    user_id: Annotated[str, Depends(get_request_user_id)],
    project_service: Annotated[ProjectService, Depends(get_project_service)],
    use_case: Annotated[Any, Depends(get_ingest_uploaded_file_use_case)],
    file: UploadFile = File(
        ...,
        description=(
            "Binary document. The original filename sets the stored ``source_file`` basename "
            "under the project directory; an existing document with the same name is replaced "
            "(vectors and SQLite assets cleared first)."
        ),
    ),
) -> IngestDocumentResponse:
    """
    **Multipart:** form field name must be ``file`` (``multipart/form-data``).

    The server reads the entire body into memory before calling the ingest use case.
    """
    buffered = await read_upload_for_ingestion(file)
    project = project_service.get_project(user_id, project_id)
    result = use_case.execute(project, buffered)
    data = ingest_document_result_to_api_dict(result)
    return IngestDocumentResponse.model_validate(data)


@router.post(
    "/{project_id}/documents/{source_file}/reindex",
    response_model=IngestDocumentResponse,
    summary="Reindex a document already on disk",
    responses={
        404: {"description": "Source file not found under the project directory"},
        502: {"description": "LLM or upstream model failure during summarization"},
        503: {"description": "Vector store, doc store, or extraction failure"},
    },
)
def post_document_reindex(
    project_id: str,
    source_file: str,
    user_id: Annotated[str, Depends(get_request_user_id)],
    project_service: Annotated[ProjectService, Depends(get_project_service)],
    use_case: Annotated[Any, Depends(get_reindex_document_use_case)],
) -> IngestDocumentResponse:
    """Rebuild vectors and assets from the file already stored for this project (URL-encode ``source_file`` if needed)."""
    project = project_service.get_project(user_id, project_id)
    result = use_case.execute(ReindexDocumentCommand(project=project, source_file=source_file))
    data = ingest_document_result_to_api_dict(result)
    return IngestDocumentResponse.model_validate(data)


@router.delete(
    "/{project_id}/documents/{source_file}",
    response_model=DeleteDocumentResponse,
    summary="Delete a document and its index rows",
    responses={
        503: {"description": "Vector store or doc store failure"},
    },
)
def delete_project_document(
    project_id: str,
    source_file: str,
    user_id: Annotated[str, Depends(get_request_user_id)],
    project_service: Annotated[ProjectService, Depends(get_project_service)],
    use_case: Annotated[Any, Depends(get_delete_document_use_case)],
) -> DeleteDocumentResponse:
    """Removes the project file, SQLite assets, FAISS vectors, and invalidates the chain cache."""
    project = project_service.get_project(user_id, project_id)
    out = use_case.execute(DeleteDocumentCommand(project=project, source_file=source_file))
    return DeleteDocumentResponse(
        source_file=out.source_file,
        file_deleted=out.file_deleted,
        deleted_vectors=out.deleted_vectors,
        deleted_assets=out.deleted_assets,
    )
