from __future__ import annotations

from collections.abc import Callable

from application.dto.ingestion import DocumentReplacementSummary
from domain.common.ports import AssetRepositoryPort, VectorStorePort
from domain.projects.project import Project


def replace_document_assets_for_reingest(
    *,
    project: Project,
    user_id: str,
    project_id: str,
    source_file: str,
    asset_repository: AssetRepositoryPort,
    vector_index: VectorStorePort,
    invalidate_project_chain: Callable[[str, str], None],
) -> DocumentReplacementSummary:
    """
    Remove existing vectors and SQLite assets for ``source_file``, then invalidate the
    retrieval cache when anything was removed.
    """
    existing_doc_ids = asset_repository.get_doc_ids_for_source_file(
        user_id=user_id,
        project_id=project_id,
        source_file=source_file,
    )

    deleted_vectors = 0
    deleted_assets = 0

    if existing_doc_ids:
        vector_index.delete_documents(project, existing_doc_ids)
        deleted_vectors = len(existing_doc_ids)

        deleted_assets = asset_repository.delete_assets_for_source_file(
            user_id=user_id,
            project_id=project_id,
            source_file=source_file,
        )

        invalidate_project_chain(user_id, project_id)

    return DocumentReplacementSummary(
        existing_doc_ids=list(existing_doc_ids),
        deleted_vectors=deleted_vectors,
        deleted_assets=deleted_assets,
    )
