"""Application rules for uploaded document bytes (name normalization, size, emptiness)."""

from __future__ import annotations

from pathlib import Path

from src.domain.buffered_document_upload import BufferedDocumentUpload


def normalize_source_filename(name: str, *, default: str = "upload") -> str:
    """Use basename only; reject path segments in the stored filename."""
    base = Path(str(name)).name.strip()
    if not base or base in {".", ".."}:
        return default
    return base


def validate_buffered_document_upload(
    upload: BufferedDocumentUpload,
    *,
    max_bytes: int,
) -> BufferedDocumentUpload:
    """
    Enforce non-empty body and size cap. Returns a copy with a normalized filename when needed.
    """
    if upload.size_bytes == 0:
        raise ValueError("Uploaded file is empty.")
    if upload.size_bytes > max_bytes:
        raise ValueError(f"Uploaded file exceeds maximum size ({max_bytes} bytes).")
    normalized = normalize_source_filename(upload.source_filename)
    if normalized == upload.source_filename:
        return upload
    return BufferedDocumentUpload(
        source_filename=normalized,
        body=upload.body,
        declared_media_type=upload.declared_media_type,
    )
