from __future__ import annotations

from collections.abc import Callable

from src.domain.project import Project
from src.services.docstore_service import DocStoreService
from src.services.ingestion_service import IngestionService
from src.services.vectorstore_service import VectorStoreService

from src.application.ingestion.dtos import IngestDocumentResult
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
        ingestion_service: IngestionService,
        docstore_service: DocStoreService,
        vectorstore_service: VectorStoreService,
        invalidate_project_chain: Callable[[str, str], None],
    ) -> None:
        self._ingestion = ingestion_service
        self._docstore = docstore_service
        self._vectorstore = vectorstore_service
        self._invalidate_chain = invalidate_project_chain

    def execute(self, project: Project, uploaded_file) -> IngestDocumentResult:
        replacement_info = replace_document_assets_for_reingest(
            project=project,
            user_id=project.user_id,
            project_id=project.project_id,
            source_file=uploaded_file.name,
            docstore_service=self._docstore,
            vectorstore_service=self._vectorstore,
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
            docstore_service=self._docstore,
            vectorstore_service=self._vectorstore,
            invalidate_project_chain=self._invalidate_chain,
        )
