"""
Request and response models for project and document management.

Identity is supplied via the ``X-User-Id`` header (see router dependencies); bodies stay minimal
and do not assume a Streamlit session.
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
