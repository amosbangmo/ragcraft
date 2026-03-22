"""
Project and document management HTTP API.

All handlers depend on application use cases (or header-derived identity + use cases only).
File ingest uses multipart form field ``file``; see each route's OpenAPI description.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, UploadFile, status

from apps.api.dependencies import (
    BackendContainerDep,
    get_create_project_use_case,
    get_delete_document_use_case,
    get_docstore_service,
    get_get_effective_retrieval_settings_use_case,
    get_ingest_uploaded_file_use_case,
    get_list_project_documents_use_case,
    get_list_projects_use_case,
    get_project_service,
    get_project_settings_service,
    get_reindex_document_use_case,
    get_request_user_id,
    get_update_project_retrieval_settings_use_case,
)
from apps.api.schemas.projects import (
    CreateProjectRequest,
    CreateProjectResponse,
    DeleteDocumentResponse,
    DocumentAssetsResponse,
    IngestDocumentResponse,
    InvalidateCacheResponse,
    ProjectDocumentDetailsResponse,
    ProjectDocumentsResponse,
    ProjectListResponse,
    ProjectRetrievalSettingsResponse,
    ProjectSummaryResponse,
    RetrievalPresetLabelResponse,
    UpdateProjectRetrievalSettingsRequest,
)
from src.application.http.wire import (
    EffectiveRetrievalSettingsWirePayload,
    IngestDocumentWirePayload,
)
from apps.api.upload_adapter import read_upload_for_ingestion
from src.application.ingestion.dtos import (
    DeleteDocumentCommand,
    IngestUploadedFileCommand,
    ReindexDocumentCommand,
)
from src.application.settings.dtos import (
    GetEffectiveRetrievalSettingsQuery,
    UpdateProjectRetrievalSettingsCommand,
)
from src.application.projects.use_cases.create_project import CreateProjectUseCase
from src.application.projects.use_cases.list_project_documents import ListProjectDocumentsUseCase
from src.application.projects.use_cases.list_projects import ListProjectsUseCase
from src.application.settings.use_cases.get_effective_retrieval_settings import (
    GetEffectiveRetrievalSettingsUseCase,
)
from src.application.settings.use_cases.update_project_retrieval_settings import (
    UpdateProjectRetrievalSettingsUseCase,
)
from src.application.ingestion.use_cases.delete_document import DeleteDocumentUseCase
from src.application.ingestion.use_cases.ingest_uploaded_file import IngestUploadedFileUseCase
from src.application.ingestion.use_cases.reindex_document import ReindexDocumentUseCase
from src.services.docstore_service import DocStoreService
from src.services.project_service import ProjectService
from src.services.project_settings_service import ProjectSettingsService

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get(
    "",
    response_model=ProjectListResponse,
    summary="List projects for a user",
)
def get_projects(
    user_id: Annotated[str, Depends(get_request_user_id)],
    use_case: Annotated[ListProjectsUseCase, Depends(get_list_projects_use_case)],
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
    use_case: Annotated[CreateProjectUseCase, Depends(get_create_project_use_case)],
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
    use_case: Annotated[ListProjectDocumentsUseCase, Depends(get_list_project_documents_use_case)],
) -> ProjectDocumentsResponse:
    """Sorted filenames at the project root (not including ``faiss_index`` or ``logs.json``)."""
    return ProjectDocumentsResponse(documents=use_case.execute(user_id, project_id))


@router.get(
    "/{project_id}/retrieval-settings",
    response_model=ProjectRetrievalSettingsResponse,
    summary="Get effective retrieval settings for a project",
)
def get_project_retrieval_settings(
    project_id: str,
    user_id: Annotated[str, Depends(get_request_user_id)],
    use_case: Annotated[
        GetEffectiveRetrievalSettingsUseCase, Depends(get_get_effective_retrieval_settings_use_case)
    ],
) -> ProjectRetrievalSettingsResponse:
    """Returns persisted preferences and merged :class:`~src.domain.retrieval_settings.RetrievalSettings` (as dict)."""
    view = use_case.execute(
        GetEffectiveRetrievalSettingsQuery(user_id=user_id, project_id=project_id)
    )
    wire = EffectiveRetrievalSettingsWirePayload.from_view(view)
    return ProjectRetrievalSettingsResponse.model_validate(wire.as_json_dict())


@router.put(
    "/{project_id}/retrieval-settings",
    response_model=ProjectRetrievalSettingsResponse,
    summary="Update persisted retrieval settings for a project",
)
def put_project_retrieval_settings(
    project_id: str,
    body: UpdateProjectRetrievalSettingsRequest,
    user_id: Annotated[str, Depends(get_request_user_id)],
    update_uc: Annotated[
        UpdateProjectRetrievalSettingsUseCase, Depends(get_update_project_retrieval_settings_use_case)
    ],
    get_uc: Annotated[
        GetEffectiveRetrievalSettingsUseCase, Depends(get_get_effective_retrieval_settings_use_case)
    ],
) -> ProjectRetrievalSettingsResponse:
    """Saves preset / advanced toggles then returns the same shape as GET."""
    update_uc.execute(
        UpdateProjectRetrievalSettingsCommand(
            user_id=user_id,
            project_id=project_id,
            retrieval_preset=body.retrieval_preset,
            retrieval_advanced=body.retrieval_advanced,
            enable_query_rewrite=body.enable_query_rewrite,
            enable_hybrid_retrieval=body.enable_hybrid_retrieval,
        )
    )
    view = get_uc.execute(
        GetEffectiveRetrievalSettingsQuery(user_id=user_id, project_id=project_id)
    )
    wire = EffectiveRetrievalSettingsWirePayload.from_view(view)
    return ProjectRetrievalSettingsResponse.model_validate(wire.as_json_dict())


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
    use_case: Annotated[IngestUploadedFileUseCase, Depends(get_ingest_uploaded_file_use_case)],
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
    result = use_case.execute(
        IngestUploadedFileCommand(project=project, uploaded_file=buffered)
    )
    wire = IngestDocumentWirePayload.from_ingest_result(result)
    return IngestDocumentResponse.model_validate(wire.as_json_dict())


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
    use_case: Annotated[ReindexDocumentUseCase, Depends(get_reindex_document_use_case)],
) -> IngestDocumentResponse:
    """Rebuild vectors and assets from the file already stored for this project (URL-encode ``source_file`` if needed)."""
    project = project_service.get_project(user_id, project_id)
    result = use_case.execute(ReindexDocumentCommand(project=project, source_file=source_file))
    wire = IngestDocumentWirePayload.from_ingest_result(result)
    return IngestDocumentResponse.model_validate(wire.as_json_dict())


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
    use_case: Annotated[DeleteDocumentUseCase, Depends(get_delete_document_use_case)],
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


@router.get(
    "/{project_id}",
    response_model=ProjectSummaryResponse,
    summary="Resolve project workspace path",
)
def get_project_summary(
    project_id: str,
    user_id: Annotated[str, Depends(get_request_user_id)],
    project_service: Annotated[ProjectService, Depends(get_project_service)],
) -> ProjectSummaryResponse:
    project = project_service.get_project(user_id, project_id)
    return ProjectSummaryResponse(
        user_id=project.user_id,
        project_id=project.project_id,
        path=str(project.path),
    )


@router.get(
    "/{project_id}/retrieval-preset-label",
    response_model=RetrievalPresetLabelResponse,
    summary="Human-readable retrieval preset label for a project",
)
def get_retrieval_preset_label(
    project_id: str,
    user_id: Annotated[str, Depends(get_request_user_id)],
    settings_service: Annotated[ProjectSettingsService, Depends(get_project_settings_service)],
) -> RetrievalPresetLabelResponse:
    label = settings_service.preset_label_for_project(user_id, project_id)
    return RetrievalPresetLabelResponse(label=label)


@router.get(
    "/{project_id}/documents/details",
    response_model=ProjectDocumentDetailsResponse,
    summary="List documents with ingestion stats",
)
def get_project_document_details(
    project_id: str,
    user_id: Annotated[str, Depends(get_request_user_id)],
    project_service: Annotated[ProjectService, Depends(get_project_service)],
    docstore: Annotated[DocStoreService, Depends(get_docstore_service)],
) -> ProjectDocumentDetailsResponse:
    project = project_service.get_project(user_id, project_id)
    documents = project_service.list_project_documents(user_id, project_id)
    details: list[dict[str, Any]] = []
    for doc_name in documents:
        file_path = project.path / doc_name
        asset_count = docstore.count_assets_for_source_file(
            user_id=user_id,
            project_id=project_id,
            source_file=doc_name,
        )
        asset_stats = docstore.get_asset_stats_for_source_file(
            user_id=user_id,
            project_id=project_id,
            source_file=doc_name,
        )
        details.append(
            {
                "name": doc_name,
                "project_id": project_id,
                "path": str(file_path),
                "size_bytes": file_path.stat().st_size if file_path.exists() else 0,
                "asset_count": asset_count,
                "text_count": int(asset_stats.get("text_count", 0)),
                "table_count": int(asset_stats.get("table_count", 0)),
                "image_count": int(asset_stats.get("image_count", 0)),
                "latest_ingested_at": asset_stats.get("latest_ingested_at"),
            }
        )
    return ProjectDocumentDetailsResponse(documents=details)


@router.get(
    "/{project_id}/documents/{source_file}/assets",
    response_model=DocumentAssetsResponse,
    summary="List indexed SQLite assets for a source file",
)
def get_document_assets(
    project_id: str,
    source_file: str,
    user_id: Annotated[str, Depends(get_request_user_id)],
    docstore: Annotated[DocStoreService, Depends(get_docstore_service)],
) -> DocumentAssetsResponse:
    assets = docstore.list_assets_for_source_file(
        user_id=user_id,
        project_id=project_id,
        source_file=source_file,
    )
    return DocumentAssetsResponse(assets=list(assets))


@router.post(
    "/{project_id}/retrieval-cache/invalidate",
    response_model=InvalidateCacheResponse,
    summary="Drop cached LangChain chain for this project",
)
def post_invalidate_retrieval_cache(
    project_id: str,
    user_id: Annotated[str, Depends(get_request_user_id)],
    container: BackendContainerDep,
) -> InvalidateCacheResponse:
    container.invalidate_project_chain(user_id, project_id)
    return InvalidateCacheResponse(ok=True)
