"""Ingestion use cases.

Package exports are lazy (``__getattr__``) so ``from … use_cases.delete_document import …`` does not
eagerly import every submodule (``ingest_file_path`` pulls optional extraction deps).
"""

from __future__ import annotations

import importlib
from typing import Any

from application.dto.ingestion import (
    DeleteDocumentCommand,
    DeleteDocumentResult,
    IngestDocumentResult,
    IngestFilePathCommand,
    IngestUploadedFileCommand,
    ReindexDocumentCommand,
)

__all__ = [
    "DeleteDocumentCommand",
    "DeleteDocumentResult",
    "DeleteDocumentUseCase",
    "IngestDocumentResult",
    "IngestFilePathCommand",
    "IngestUploadedFileCommand",
    "IngestFilePathUseCase",
    "IngestUploadedFileUseCase",
    "ReindexDocumentCommand",
    "ReindexDocumentUseCase",
    "replace_document_assets_for_reingest",
]

_LAZY_ATTRS: dict[str, tuple[str, str]] = {
    "DeleteDocumentUseCase": ("delete_document", "DeleteDocumentUseCase"),
    "IngestFilePathUseCase": ("ingest_file_path", "IngestFilePathUseCase"),
    "IngestUploadedFileUseCase": ("ingest_uploaded_file", "IngestUploadedFileUseCase"),
    "ReindexDocumentUseCase": ("reindex_document", "ReindexDocumentUseCase"),
    "replace_document_assets_for_reingest": (
        "replace_document_assets",
        "replace_document_assets_for_reingest",
    ),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_ATTRS:
        mod_name, attr = _LAZY_ATTRS[name]
        mod = importlib.import_module(f"{__name__}.{mod_name}")
        return getattr(mod, attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
