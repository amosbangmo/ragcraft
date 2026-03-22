from __future__ import annotations

from collections.abc import Callable

from src.domain.ports import AssetRepositoryPort, VectorStorePort
from src.domain.ports.document_ingestion_port import DocumentIngestionPort

from src.application.ingestion.dtos import IngestDocumentResult, IngestUploadedFileCommand

from .ingest_common import finalize_ingestion_pipeline
from .replace_document_assets import replace_document_assets_for_reingest


class IngestUploadedFileUseCase:
    """
    Save an uploaded file into the project workspace, replace any prior index rows for that
    filename, then run the same pipeline as :class:`IngestFilePathUseCase`.
    """

    def __init__(
        self,
        *,
        ingestion_service: DocumentIngestionPort,
        asset_repository: AssetRepositoryPort,
        vector_index: VectorStorePort,
        invalidate_project_chain: Callable[[str, str], None],
    ) -> None:
        self._ingestion = ingestion_service
        self._assets = asset_repository
        self._vectors = vector_index
        self._invalidate_chain = invalidate_project_chain

    def execute(self, command: IngestUploadedFileCommand) -> IngestDocumentResult:
        project = command.project
        uploaded_file = command.uploaded_file
        replacement_info = replace_document_assets_for_reingest(
            project=project,
            user_id=project.user_id,
            project_id=project.project_id,
            source_file=uploaded_file.name,
            asset_repository=self._assets,
            vector_index=self._vectors,
            invalidate_project_chain=self._invalidate_chain,
        )

        summary_documents, raw_assets, diagnostics = self._ingestion.ingest_uploaded_file(
            project,
            uploaded_file,
        )

        return finalize_ingestion_pipeline(
            project=project,
            user_id=project.user_id,
            project_id=project.project_id,
            source_file=uploaded_file.name,
            summary_documents=summary_documents,
            raw_assets=raw_assets,
            diagnostics=diagnostics,
            replacement_info=replacement_info,
            asset_repository=self._assets,
            vector_index=self._vectors,
            invalidate_project_chain=self._invalidate_chain,
        )
