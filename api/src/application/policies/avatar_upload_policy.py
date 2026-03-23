"""Application validation for bounded avatar uploads (defense in depth beyond transport caps)."""

from __future__ import annotations

from domain.projects.buffered_document_upload import BufferedDocumentUpload
from infrastructure.config.config import USER_PROFILE_UPLOAD_CONFIG


def validate_buffered_avatar_upload(upload: BufferedDocumentUpload) -> BufferedDocumentUpload:
    """Require non-empty body and size within ``USER_PROFILE_UPLOAD_CONFIG.max_avatar_bytes``."""
    if upload.size_bytes == 0:
        raise ValueError("Avatar upload is empty.")
    if upload.size_bytes > USER_PROFILE_UPLOAD_CONFIG.max_avatar_bytes:
        raise ValueError(
            f"Avatar exceeds maximum size ({USER_PROFILE_UPLOAD_CONFIG.max_avatar_bytes} bytes)."
        )
    return upload
