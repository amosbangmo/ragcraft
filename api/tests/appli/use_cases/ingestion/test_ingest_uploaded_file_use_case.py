from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from application.dto.ingestion import IngestUploadedFileCommand
from application.use_cases.ingestion.ingest_uploaded_file import IngestUploadedFileUseCase
from domain.projects.buffered_document_upload import BufferedDocumentUpload
from domain.projects.project import Project


def test_ingest_rejects_empty_upload_body() -> None:
    project = Project(user_id="u", project_id="p")
    ingestion = MagicMock()
    uc = IngestUploadedFileUseCase(
        ingestion_service=ingestion,
        asset_repository=MagicMock(),
        vector_index=MagicMock(),
        invalidate_project_chain=lambda *_a, **_k: None,
    )
    cmd = IngestUploadedFileCommand(
        project=project,
        upload=BufferedDocumentUpload(source_filename="a.txt", body=b""),
    )
    with pytest.raises(ValueError, match="empty"):
        uc.execute(cmd)
    ingestion.ingest_uploaded_file.assert_not_called()
