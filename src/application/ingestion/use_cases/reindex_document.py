from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from src.domain.ports import AssetRepositoryPort, VectorStorePort

from src.application.ingestion.dtos import (
    IngestDocumentResult,
    IngestFilePathCommand,
    ReindexDocumentCommand,
)
from .ingest_common import resolve_project_file_path
from .ingest_file_path import IngestFilePathUseCase
from .replace_document_assets import replace_document_assets_for_reingest

if TYPE_CHECKING:
    from src.infrastructure.services.ingestion_service import IngestionService


class ReindexDocumentUseCase:
    """
    Command-style re-ingestion: drop existing vectors/assets for a source file, then rebuild
    from the file already on disk under the project directory.
    """

    def __init__(
        self,
        *,
        ingestion_service: IngestionService,
        asset_repository: AssetRepositoryPort,
        vector_index: VectorStorePort,
        invalidate_project_chain: Callable[[str, str], None],
    ) -> None:
        self._assets = asset_repository
        self._vectors = vector_index
        self._invalidate_chain = invalidate_project_chain
        self._ingest_path = IngestFilePathUseCase(
            ingestion_service=ingestion_service,
            asset_repository=asset_repository,
            vector_index=vector_index,
            invalidate_project_chain=invalidate_project_chain,
        )

    def execute(self, command: ReindexDocumentCommand) -> IngestDocumentResult:
        project = command.project
        source_file = command.source_file
        file_path = resolve_project_file_path(project, source_file)

        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError(f"Document not found on disk: {source_file}")

        replacement_info = replace_document_assets_for_reingest(
            project=project,
            user_id=project.user_id,
            project_id=project.project_id,
            source_file=source_file,
            asset_repository=self._assets,
            vector_index=self._vectors,
            invalidate_project_chain=self._invalidate_chain,
        )

        return self._ingest_path.execute(
            IngestFilePathCommand(
                project=project,
                file_path=file_path,
                source_file=source_file,
                replacement_info=replacement_info,
            )
        )
