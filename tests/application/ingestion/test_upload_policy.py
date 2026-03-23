from __future__ import annotations

import pytest

from src.domain.buffered_document_upload import BufferedDocumentUpload
from src.application.ingestion.upload_policy import normalize_source_filename, validate_buffered_document_upload


def test_normalize_strips_path_segments() -> None:
    assert normalize_source_filename(r"..\..\secret.pdf") == "secret.pdf"


def test_validate_rejects_empty_body() -> None:
    up = BufferedDocumentUpload(source_filename="a.txt", body=b"")
    with pytest.raises(ValueError, match="empty"):
        validate_buffered_document_upload(up, max_bytes=100)


def test_validate_rejects_oversize() -> None:
    up = BufferedDocumentUpload(source_filename="a.txt", body=b"x" * 10)
    with pytest.raises(ValueError, match="exceeds"):
        validate_buffered_document_upload(up, max_bytes=5)


def test_validate_normalizes_filename() -> None:
    up = BufferedDocumentUpload(source_filename="nested/name.txt", body=b"ok")
    out = validate_buffered_document_upload(up, max_bytes=100)
    assert out.source_filename == "name.txt"
