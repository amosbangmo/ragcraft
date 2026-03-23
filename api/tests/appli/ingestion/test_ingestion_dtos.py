"""Lightweight ingestion application-layer tests (DTOs only; avoids heavy use_cases package init)."""

from __future__ import annotations

from domain.projects.buffered_document_upload import BufferedDocumentUpload
from domain.common.ingestion_diagnostics import IngestionDiagnostics
from domain.projects.project import Project
from application.dto.ingestion import (
    DeleteDocumentResult,
    IngestDocumentResult,
    IngestUploadedFileCommand,
)


def test_ingest_upload_file_command_holds_handles() -> None:
    project = Project(user_id="u", project_id="p")
    upload = BufferedDocumentUpload(source_filename="doc.pdf", body=b"x")
    cmd = IngestUploadedFileCommand(project=project, upload=upload)
    assert cmd.project is project
    assert cmd.upload is upload


def test_ingest_result_format_first_upload_message() -> None:
    result = IngestDocumentResult(
        raw_assets=[{"content_type": "text"}, {"content_type": "text"}],
        replacement_info={"deleted_assets": 0, "deleted_vectors": 0},
        diagnostics=IngestionDiagnostics(),
    )
    msg = result.format_ingestion_success_message("a.pdf")
    assert "a.pdf" in msg
    assert "processed 2 multimodal asset(s)" in msg
    assert "replaced previous" not in msg


def test_ingest_result_format_after_replace_message() -> None:
    result = IngestDocumentResult(
        raw_assets=[{"content_type": "table"}],
        replacement_info={"deleted_assets": 3, "deleted_vectors": 2},
        diagnostics=IngestionDiagnostics(),
    )
    msg = result.format_ingestion_success_message("b.docx")
    assert "replaced previous ingestion" in msg
    assert "3 SQLite asset(s) removed" in msg
    assert "2 FAISS vector(s) removed" in msg


def test_ingest_result_format_reindex_message() -> None:
    result = IngestDocumentResult(
        raw_assets=[{"content_type": "image"}, {"content_type": "image"}],
        replacement_info={"deleted_assets": 1, "deleted_vectors": 1},
        diagnostics=IngestionDiagnostics(),
    )
    msg = result.format_reindex_success_message("c.pptx")
    assert "reindexed successfully" in msg
    assert "replaced" in msg
    assert "generated 2 multimodal asset(s)" in msg


def test_delete_result_format_summary() -> None:
    r = DeleteDocumentResult(
        source_file="x.pdf",
        file_deleted=True,
        deleted_vectors=2,
        deleted_assets=4,
    )
    s = r.format_delete_summary("x.pdf")
    assert "file deleted=True" in s
    assert "SQLite assets removed=4" in s
