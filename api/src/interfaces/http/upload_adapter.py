"""
FastAPI / Starlette multipart → domain :class:`~domain.buffered_document_upload.BufferedDocumentUpload`.

**Policy — bounded chunked buffering (not streaming into business logic):**

- Each body is read in ``_READ_CHUNK``-sized slices while tracking cumulative size.
- If the limit is exceeded mid-stream, :class:`StarletteUploadTooLargeError` is raised immediately
  (no full-file buffer for oversized uploads).
- After a successful read, bytes are concatenated into a single buffer for the application layer.
  True streaming from the socket into extraction/indexing is **not** implemented; document
  ingestion persists then runs the on-disk pipeline. See ``application.ingestion.upload_boundary``.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import UploadFile

from domain.projects.buffered_document_upload import BufferedDocumentUpload
from infrastructure.config.config import INGESTION_CONFIG, USER_PROFILE_UPLOAD_CONFIG

_READ_CHUNK = 1024 * 1024


class StarletteUploadPayloadError(ValueError):
    """Invalid or unreadable multipart upload (client error)."""


class StarletteUploadTooLargeError(StarletteUploadPayloadError):
    """Total body size exceeds the configured cap for this upload kind."""


def _client_filename(upload: UploadFile, *, default_name: str) -> str:
    raw = (upload.filename or "").strip() or default_name
    base = Path(raw).name.strip()
    return base if base and base not in {".", ".."} else default_name


async def _read_starlette_upload_bounded(
    upload: UploadFile,
    *,
    default_name: str,
    max_bytes: int,
) -> BufferedDocumentUpload:
    """
    Read upload body in chunks until EOF or ``max_bytes`` exceeded.

    Raises:
        StarletteUploadTooLargeError: if more than ``max_bytes`` would be required.
        StarletteUploadPayloadError: if the stream cannot be read.
    """
    name = _client_filename(upload, default_name=default_name)
    chunks: list[bytes] = []
    total = 0
    try:
        while True:
            chunk = await upload.read(_READ_CHUNK)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise StarletteUploadTooLargeError(
                    f"Upload exceeds maximum size of {max_bytes} bytes."
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


async def read_buffered_document_upload(
    upload: UploadFile,
    *,
    default_name: str = "upload",
    max_bytes: int | None = None,
) -> BufferedDocumentUpload:
    """
    Document ingest: read up to ``max_bytes`` (default: ``INGESTION_CONFIG.max_upload_bytes`` /
    ``RAG_MAX_UPLOAD_BYTES``).

    Raises:
        StarletteUploadTooLargeError: if more than ``max_bytes`` would be required.
        StarletteUploadPayloadError: if the stream cannot be read.
    """
    limit = INGESTION_CONFIG.max_upload_bytes if max_bytes is None else max_bytes
    return await _read_starlette_upload_bounded(upload, default_name=default_name, max_bytes=limit)


async def read_buffered_avatar_upload(
    upload: UploadFile,
    *,
    default_name: str = "avatar",
) -> BufferedDocumentUpload:
    """
    Profile avatar: read up to ``USER_PROFILE_UPLOAD_CONFIG.max_avatar_bytes`` /
    ``RAG_MAX_AVATAR_UPLOAD_BYTES`` (default 2 MiB).

    Same chunked policy as :func:`read_buffered_document_upload`.
    """
    return await _read_starlette_upload_bounded(
        upload,
        default_name=default_name,
        max_bytes=USER_PROFILE_UPLOAD_CONFIG.max_avatar_bytes,
    )
