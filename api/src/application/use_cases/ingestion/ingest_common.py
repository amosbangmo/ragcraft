from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

from application.dto.ingestion import DocumentReplacementSummary, IngestDocumentResult
from domain.projects.documents.stored_multimodal_asset import StoredMultimodalAsset
from application.ingestion.ingestion_diagnostics_log import log_ingestion_diagnostics
from domain.common.ingestion_diagnostics import IngestionDiagnostics
from domain.common.ports import AssetRepositoryPort, VectorStorePort
from domain.projects.project import Project
from domain.rag.summary_recall_document import SummaryRecallDocument


def finalize_ingestion_pipeline(
    *,
    project: Project,
    user_id: str,
    project_id: str,
    source_file: str,
    summary_documents: Sequence[Any],
    raw_assets: Sequence[Any],
    diagnostics: IngestionDiagnostics,
    replacement_info: DocumentReplacementSummary,
    asset_repository: AssetRepositoryPort,
    vector_index: VectorStorePort,
    invalidate_project_chain: Callable[[str, str], None],
) -> IngestDocumentResult:
    if not raw_assets:
        raise ValueError(f"No raw assets generated for file: {source_file}")

    stored_assets: list[StoredMultimodalAsset] = []
    for asset in raw_assets:
        row = (
            asset
            if isinstance(asset, StoredMultimodalAsset)
            else StoredMultimodalAsset.from_mapping(asset)
        )
        stored_assets.append(row)
        asset_repository.upsert_asset(**row.upsert_kwargs())

    indexing_ms = 0.0
    if summary_documents:
        chunks = [
            SummaryRecallDocument(
                page_content=str(getattr(d, "page_content", "") or ""),
                metadata=dict(getattr(d, "metadata", None) or {}),
            )
            for d in summary_documents
        ]
        _, indexing_ms = vector_index.index_documents(project, chunks)

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
        raw_assets=stored_assets,
        replacement_info=replacement_info,
        diagnostics=diagnostics,
    )


def default_empty_replacement_info() -> DocumentReplacementSummary:
    return DocumentReplacementSummary(existing_doc_ids=[], deleted_vectors=0, deleted_assets=0)


def resolve_project_file_path(project: Project, source_file: str) -> Path:
    return project.path / source_file
