"""
Bounded in-memory representation of an HTTP-multipart upload after transport adaptation.

Used for **document ingestion** and **profile avatar** uploads: the API adapter reads the body in
chunks with a byte cap, then passes this type into application use cases (no ``UploadFile`` in
``src/application``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BufferedDocumentUpload:
    """
    Application-visible upload payload after transport has read bytes.

    Implements the structural contract expected by :func:`infrastructure.rag.ingestion.loader.save_uploaded_file`
    (``name`` + ``getbuffer()``).
    """

    source_filename: str
    body: bytes
    declared_media_type: str | None = None

    @property
    def name(self) -> str:
        return self.source_filename

    def getbuffer(self) -> memoryview:
        return memoryview(self.body)

    @property
    def size_bytes(self) -> int:
        return len(self.body)

    @classmethod
    def from_duck_typed(cls, obj: Any, *, default_name: str = "upload") -> BufferedDocumentUpload:
        """Build from Streamlit ``UploadedFile`` or any object with ``name`` and ``getbuffer()``."""
        raw_name = (getattr(obj, "name", None) or default_name) or default_name
        getbuffer = getattr(obj, "getbuffer", None)
        if getbuffer is None:
            raise TypeError("uploaded_file must expose getbuffer()")
        body = bytes(getbuffer())
        media = getattr(obj, "type", None)
        if media is not None and not isinstance(media, str):
            media = str(media) if media else None
        return cls(
            source_filename=str(raw_name).strip() or default_name,
            body=body,
            declared_media_type=media,
        )
