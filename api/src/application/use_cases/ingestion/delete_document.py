from __future__ import annotations

from collections.abc import Callable

from application.dto.ingestion import DeleteDocumentCommand, DeleteDocumentResult
from domain.common.ports import AssetRepositoryPort, VectorStorePort

from .ingest_common import resolve_project_file_path


class DeleteDocumentUseCase:
    """Remove FAISS vectors, SQLite assets, the project file, and invalidate the chain cache."""

    def __init__(
        self,
        *,
        asset_repository: AssetRepositoryPort,
        vector_index: VectorStorePort,
        invalidate_project_chain: Callable[[str, str], None],
    ) -> None:
        self._assets = asset_repository
        self._vectors = vector_index
        self._invalidate_chain = invalidate_project_chain

    def execute(self, command: DeleteDocumentCommand) -> DeleteDocumentResult:
        project = command.project
        source_file = command.source_file
        user_id = project.user_id
        project_id = project.project_id
        file_path = resolve_project_file_path(project, source_file)

        existing_doc_ids = self._assets.get_doc_ids_for_source_file(
            user_id=user_id,
            project_id=project_id,
            source_file=source_file,
        )

        deleted_vectors = 0
        deleted_assets = 0
        file_deleted = False

        if existing_doc_ids:
            self._vectors.delete_documents(project, existing_doc_ids)
            deleted_vectors = len(existing_doc_ids)

            deleted_assets = self._assets.delete_assets_for_source_file(
                user_id=user_id,
                project_id=project_id,
                source_file=source_file,
            )

        if file_path.exists() and file_path.is_file():
            file_path.unlink()
            file_deleted = True

        self._invalidate_chain(user_id, project_id)

        return DeleteDocumentResult(
            source_file=source_file,
            file_deleted=file_deleted,
            deleted_vectors=deleted_vectors,
            deleted_assets=deleted_assets,
        )
