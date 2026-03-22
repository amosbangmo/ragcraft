from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from langchain_core.documents import Document

from src.application.ingestion.ingestion_diagnostics_log import log_ingestion_diagnostics
from src.domain.ingestion_diagnostics import IngestionDiagnostics
from src.domain.ports import AssetRepositoryPort, VectorStorePort
from src.domain.project import Project

from src.application.ingestion.dtos import IngestDocumentResult


def finalize_ingestion_pipeline(
    *,
    project: Project,
    user_id: str,
    project_id: str,
    source_file: str,
    summary_documents: list[Document],
    raw_assets: list[dict],
    diagnostics: IngestionDiagnostics,
    replacement_info: dict,
    asset_repository: AssetRepositoryPort,
    vector_index: VectorStorePort,
    invalidate_project_chain: Callable[[str, str], None],
) -> IngestDocumentResult:
    if not raw_assets:
        raise ValueError(f"No raw assets generated for file: {source_file}")

    for asset in raw_assets:
        asset_repository.upsert_asset(**asset)

    indexing_ms = 0.0
    if summary_documents:
        _, indexing_ms = vector_index.index_documents(project, summary_documents)

    diagnostics = replace(
        diagnostics,
        indexing_ms=indexing_ms,
        total_ms=diagnostics.extraction_ms + diagnostics.summarization_ms + indexing_ms,
    )

    invalidate_project_chain(user_id, project_id)

    log_ingestion_diagnostics(
        user_id=user_id,
        project_id=project_id,
        source_file=source_file,
        diagnostics=diagnostics,
    )

    return IngestDocumentResult(
        raw_assets=raw_assets,
        replacement_info=replacement_info,
        diagnostics=diagnostics,
    )


def default_empty_replacement_info() -> dict:
    return {
        "existing_doc_ids": [],
        "deleted_vectors": 0,
        "deleted_assets": 0,
    }


def resolve_project_file_path(project: Project, source_file: str) -> Path:
    return project.path / source_file
