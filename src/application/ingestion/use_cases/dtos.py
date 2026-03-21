from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.domain.ingestion_diagnostics import IngestionDiagnostics
from src.domain.project import Project


@dataclass(frozen=True)
class IngestFilePathCommand:
    """Ingest an on-disk file that already lives under the project workspace."""

    project: Project
    file_path: str | Path
    source_file: str
    replacement_info: dict | None = None


@dataclass(frozen=True)
class ReindexDocumentCommand:
    """Re-extract, summarize, persist, and re-index a document already stored for the project."""

    project: Project
    source_file: str


@dataclass(frozen=True)
class DeleteDocumentCommand:
    """Remove vectors, SQLite assets, the on-disk file, and invalidate the project chain."""

    project: Project
    source_file: str


@dataclass
class IngestDocumentResult:
    raw_assets: list[dict]
    replacement_info: dict
    diagnostics: IngestionDiagnostics

    def as_payload(self) -> dict:
        return {
            "raw_assets": self.raw_assets,
            "replacement_info": self.replacement_info,
            "diagnostics": self.diagnostics,
        }


@dataclass
class DeleteDocumentResult:
    source_file: str
    file_deleted: bool
    deleted_vectors: int
    deleted_assets: int

    def as_payload(self) -> dict:
        return {
            "source_file": self.source_file,
            "file_deleted": self.file_deleted,
            "deleted_vectors": self.deleted_vectors,
            "deleted_assets": self.deleted_assets,
        }
