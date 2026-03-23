"""
FastAPI / Starlette multipart → domain :class:`~src.domain.buffered_document_upload.BufferedDocumentUpload`.

**Policy:** uploads are read in chunks with a hard byte cap so oversized bodies are rejected without
buffering the full file. True streaming into extraction is not supported yet; the bounded buffer is
passed to the application use case, which persists then runs the existing on-disk pipeline.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import UploadFile

from src.core.config import INGESTION_CONFIG
from src.domain.buffered_document_upload import BufferedDocumentUpload

_READ_CHUNK = 1024 * 1024


class StarletteUploadPayloadError(ValueError):
    """Invalid or unreadable multipart upload (client error)."""


class StarletteUploadTooLargeError(StarletteUploadPayloadError):
    """Total body size exceeds configured ``RAG_MAX_UPLOAD_BYTES`` / :attr:`INGESTION_CONFIG.max_upload_bytes`."""


def _client_filename(upload: UploadFile, *, default_name: str) -> str:
    raw = (upload.filename or "").strip() or default_name
    base = Path(raw).name.strip()
    return base if base and base not in {".", ".."} else default_name


async def read_buffered_document_upload(
    upload: UploadFile,
    *,
    default_name: str = "upload",
    max_bytes: int | None = None,
) -> BufferedDocumentUpload:
    """
    Read the upload body up to ``max_bytes`` (default: ingestion config).

    Raises:
        StarletteUploadTooLargeError: if more than ``max_bytes`` would be required.
        StarletteUploadPayloadError: if the stream cannot be read.
    """
    limit = INGESTION_CONFIG.max_upload_bytes if max_bytes is None else max_bytes
    name = _client_filename(upload, default_name=default_name)
    chunks: list[bytes] = []
    total = 0
    try:
        while True:
            chunk = await upload.read(_READ_CHUNK)
            if not chunk:
                break
            total += len(chunk)
            if total > limit:
                raise StarletteUploadTooLargeError(
                    f"Upload exceeds maximum size of {limit} bytes (configured via RAG_MAX_UPLOAD_BYTES)."
                )
            chunks.append(chunk)
    except StarletteUploadTooLargeError:
        raise
    except Exception as exc:
        raise StarletteUploadPayloadError(f"Failed to read upload body: {exc}") from exc

    body = b"".join(chunks)
    media = upload.content_type
    return BufferedDocumentUpload(
        source_filename=name,
        body=body,
        declared_media_type=media,
    )
