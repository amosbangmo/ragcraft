from __future__ import annotations

from collections.abc import Callable

from src.services.docstore_service import DocStoreService
from src.services.ingestion_service import IngestionService
from src.services.vectorstore_service import VectorStoreService

from .dtos import IngestDocumentResult, IngestFilePathCommand, ReindexDocumentCommand
from .ingest_common import resolve_project_file_path
from .ingest_file_path import IngestFilePathUseCase
from .replace_document_assets import replace_document_assets_for_reingest


class ReindexDocumentUseCase:
    """
    Command-style re-ingestion: drop existing vectors/assets for a source file, then rebuild
    from the file already on disk under the project directory.
    """

    def __init__(
        self,
        *,
        ingestion_service: IngestionService,
        docstore_service: DocStoreService,
        vectorstore_service: VectorStoreService,
        invalidate_project_chain: Callable[[str, str], None],
    ) -> None:
        self._docstore = docstore_service
        self._vectorstore = vectorstore_service
        self._invalidate_chain = invalidate_project_chain
        self._ingest_path = IngestFilePathUseCase(
            ingestion_service=ingestion_service,
            docstore_service=docstore_service,
            vectorstore_service=vectorstore_service,
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
            docstore_service=self._docstore,
            vectorstore_service=self._vectorstore,
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
