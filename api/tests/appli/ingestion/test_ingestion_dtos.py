"""Lightweight ingestion application-layer tests (DTOs only; avoids heavy use_cases package init)."""

from __future__ import annotations

from application.dto.ingestion import (
    DeleteDocumentResult,
    DocumentReplacementSummary,
    IngestDocumentResult,
    IngestUploadedFileCommand,
)
from domain.projects.documents.stored_multimodal_asset import StoredMultimodalAsset
from domain.common.ingestion_diagnostics import IngestionDiagnostics
from domain.projects.buffered_document_upload import BufferedDocumentUpload
from domain.projects.project import Project


def _asset(content_type: str) -> StoredMultimodalAsset:
    return StoredMultimodalAsset.from_mapping(
        {
            "doc_id": "d",
            "user_id": "u",
            "project_id": "p",
            "source_file": "f",
            "content_type": content_type,
            "raw_content": "",
            "summary": "",
            "metadata": {},
        }
    )


def test_ingest_upload_file_command_holds_handles() -> None:
    project = Project(user_id="u", project_id="p")
    upload = BufferedDocumentUpload(source_filename="doc.pdf", body=b"x")
    cmd = IngestUploadedFileCommand(project=project, upload=upload)
    assert cmd.project is project
    assert cmd.upload is upload


def test_ingest_result_format_first_upload_message() -> None:
    result = IngestDocumentResult(
        raw_assets=[_asset("text"), _asset("text")],
        replacement_info=DocumentReplacementSummary([], 0, 0),
        diagnostics=IngestionDiagnostics(),
    )
    msg = result.format_ingestion_success_message("a.pdf")
    assert "a.pdf" in msg
    assert "processed 2 multimodal asset(s)" in msg
    assert "replaced previous" not in msg


def test_ingest_result_format_after_replace_message() -> None:
    result = IngestDocumentResult(
        raw_assets=[_asset("table")],
        replacement_info=DocumentReplacementSummary([], 2, 3),
        diagnostics=IngestionDiagnostics(),
    )
    msg = result.format_ingestion_success_message("b.docx")
    assert "replaced previous ingestion" in msg
    assert "3 SQLite asset(s) removed" in msg
    assert "2 FAISS vector(s) removed" in msg


def test_ingest_result_format_reindex_message() -> None:
    result = IngestDocumentResult(
        raw_assets=[_asset("image"), _asset("image")],
        replacement_info=DocumentReplacementSummary([], 1, 1),
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
