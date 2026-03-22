"""
Request and response models for project and document management.

Identity is supplied via the ``X-User-Id`` header (see router dependencies); request bodies stay minimal.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CreateProjectRequest(BaseModel):
    """Create or ensure a project workspace."""

    model_config = {"extra": "forbid"}

    project_id: str = Field(
        ...,
        min_length=1,
        description="Directory name under the user's projects folder.",
        examples=["my-rag-project"],
    )


class CreateProjectResponse(BaseModel):
    model_config = {"extra": "forbid"}

    project_id: str = Field(description="Echo of the created or ensured project id.")


class ProjectListResponse(BaseModel):
    model_config = {"extra": "forbid"}

    projects: list[str] = Field(
        default_factory=list,
        description="Sorted project directory names for the requesting user.",
    )


class ProjectDocumentsResponse(BaseModel):
    model_config = {"extra": "forbid"}

    documents: list[str] = Field(
        default_factory=list,
        description="Sorted source filenames at the project root (excludes index and logs).",
    )


class IngestionDiagnosticsPayload(BaseModel):
    model_config = {"extra": "forbid"}

    extraction_ms: float = 0.0
    summarization_ms: float = 0.0
    indexing_ms: float = 0.0
    total_ms: float = 0.0
    extracted_elements: int = 0
    generated_assets: int = 0
    errors: list[str] = Field(default_factory=list)


class IngestDocumentResponse(BaseModel):
    """Result of ingest or reindex (multimodal assets + replacement stats + timing)."""

    model_config = {"extra": "forbid"}

    raw_assets: list[dict[str, Any]] = Field(default_factory=list)
    replacement_info: dict[str, Any] = Field(default_factory=dict)
    diagnostics: IngestionDiagnosticsPayload


class DeleteDocumentResponse(BaseModel):
    model_config = {"extra": "forbid"}

    source_file: str
    file_deleted: bool
    deleted_vectors: int
    deleted_assets: int


class ProjectRetrievalSettingsResponse(BaseModel):
    """Persisted preferences plus merged effective retrieval tuning."""

    model_config = {"extra": "forbid"}

    preferences: dict[str, Any] = Field(default_factory=dict)
    effective_retrieval: dict[str, Any] = Field(default_factory=dict)


class ProjectSummaryResponse(BaseModel):
    model_config = {"extra": "forbid"}

    user_id: str
    project_id: str
    path: str = Field(description="Absolute workspace path for this project.")


class RetrievalPresetLabelResponse(BaseModel):
    model_config = {"extra": "forbid"}

    label: str


class ProjectDocumentDetailItem(BaseModel):
    """Per-source-file workspace and docstore stats (transport shape for document lists)."""

    model_config = {"extra": "forbid"}

    name: str = Field(..., description="Source filename at project root.")
    project_id: str
    path: str = Field(..., description="Absolute path to the file on the API host.")
    size_bytes: int = 0
    asset_count: int = 0
    text_count: int = 0
    table_count: int = 0
    image_count: int = 0
    latest_ingested_at: str | None = Field(
        default=None,
        description="ISO-8601 latest asset created_at for this source file, if any.",
    )


class ProjectDocumentDetailsResponse(BaseModel):
    model_config = {"extra": "forbid"}

    documents: list[ProjectDocumentDetailItem] = Field(
        default_factory=list,
        description="Per-file stats for the project document list.",
    )


class DocumentAssetRow(BaseModel):
    """One row from the SQLite multimodal asset store for a source file."""

    model_config = {"extra": "forbid"}

    doc_id: str
    user_id: str
    project_id: str
    source_file: str
    content_type: str
    raw_content: str
    summary: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None


class DocumentAssetsResponse(BaseModel):
    model_config = {"extra": "forbid"}

    assets: list[DocumentAssetRow] = Field(default_factory=list)


class InvalidateCacheResponse(BaseModel):
    model_config = {"extra": "forbid"}

    ok: bool = True


class UpdateProjectRetrievalSettingsRequest(BaseModel):
    model_config = {"extra": "forbid"}

    retrieval_preset: str = Field(..., min_length=1, description="precise | balanced | exploratory")
    retrieval_advanced: bool = False
    enable_query_rewrite: bool = True
    enable_hybrid_retrieval: bool = True
