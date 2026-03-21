"""
Bridge FastAPI ``UploadFile`` to the ingestion layer, which expects Streamlit-like objects
(``name`` + ``getbuffer()``) via :func:`src.infrastructure.ingestion.loader.save_uploaded_file`.
"""

from __future__ import annotations

from fastapi import UploadFile


async def read_upload_for_ingestion(upload: UploadFile, *, default_name: str = "upload") -> object:
    """
    Read the full upload body and return a small object compatible with ``save_uploaded_file``.

    The returned object's ``name`` is the client filename (or ``default_name`` if missing).
    That name is used as ``source_file`` in the project workspace (same as the saved basename).
    """
    data = await upload.read()
    raw_name = (upload.filename or "").strip() or default_name

    class _BufferedUpload:
        __slots__ = ("name", "_data")

        def __init__(self, name: str, body: bytes) -> None:
            self.name = name
            self._data = body

        def getbuffer(self) -> memoryview:
            return memoryview(self._data)

    return _BufferedUpload(raw_name, data)
