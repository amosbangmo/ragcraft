from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from src.domain.ports import AssetRepositoryPort, VectorStorePort

from src.application.ingestion.dtos import IngestDocumentResult, IngestFilePathCommand

if TYPE_CHECKING:
    from src.services.ingestion_service import IngestionService
from .ingest_common import (
    default_empty_replacement_info,
    finalize_ingestion_pipeline,
)


class IngestFilePathUseCase:
    """
    Extract, summarize, parse tables, persist assets, and index vectors for a file path.
    Does not remove prior assets unless ``replacement_info`` is precomputed by the caller.
    """

    def __init__(
        self,
        *,
        ingestion_service: IngestionService,
        asset_repository: AssetRepositoryPort,
        vector_index: VectorStorePort,
        invalidate_project_chain: Callable[[str, str], None],
    ) -> None:
        self._ingestion = ingestion_service
        self._assets = asset_repository
        self._vectors = vector_index
        self._invalidate_chain = invalidate_project_chain

    def execute(self, command: IngestFilePathCommand) -> IngestDocumentResult:
        project = command.project
        replacement_info = command.replacement_info or default_empty_replacement_info()

        summary_documents, raw_assets, diagnostics = self._ingestion.ingest_file_path(
            project=project,
            file_path=command.file_path,
            source_file=command.source_file,
        )

        return finalize_ingestion_pipeline(
            project=project,
            user_id=project.user_id,
            project_id=project.project_id,
            source_file=command.source_file,
            summary_documents=summary_documents,
            raw_assets=raw_assets,
            diagnostics=diagnostics,
            replacement_info=replacement_info,
            asset_repository=self._assets,
            vector_index=self._vectors,
            invalidate_project_chain=self._invalidate_chain,
        )
