"""
Multipart upload boundary for HTTP-originated file bytes.

**Strategy (explicit): bounded chunked buffering — not true streaming into parsers.**

1. ``interfaces.http.upload_adapter`` reads each :class:`starlette.datastructures.UploadFile` in
   fixed-size chunks (default 1 MiB).
2. While reading, it accumulates total size and raises if the configured cap is exceeded, so
   oversized bodies are rejected **without** buffering the full file first.
3. The full body is held in memory only **after** the cap check passes; the resulting
   :class:`~domain.buffered_document_upload.BufferedDocumentUpload` is passed into application
   use cases.

**Document ingestion** uses ``INGESTION_CONFIG.max_upload_bytes`` (``RAG_MAX_UPLOAD_BYTES``).
**Avatar uploads** use ``USER_PROFILE_UPLOAD_CONFIG.max_avatar_bytes``
(``RAG_MAX_AVATAR_UPLOAD_BYTES``).

Extraction and indexing for documents still run from **persisted files** on disk (existing
pipeline); bytes are not streamed from the socket directly into unstructured.
"""

from __future__ import annotations

from domain.projects.buffered_document_upload import BufferedDocumentUpload

__all__ = ["BufferedDocumentUpload"]
