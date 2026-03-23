from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from domain.common.ingestion_diagnostics import IngestionDiagnostics
from domain.projects.buffered_document_upload import BufferedDocumentUpload
from domain.projects.project import Project


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


@dataclass(frozen=True)
class IngestUploadedFileCommand:
    """Ingest a buffered upload (transport builds :class:`~domain.buffered_document_upload.BufferedDocumentUpload`)."""

    project: Project
    upload: BufferedDocumentUpload


@dataclass
class IngestDocumentResult:
    raw_assets: list[dict]
    replacement_info: dict
    diagnostics: IngestionDiagnostics

    def content_type_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for asset in self.raw_assets:
            ct = asset.get("content_type") or "unknown"
            counts[ct] = counts.get(ct, 0) + 1
        return counts

    def _replacement_deleted_assets(self) -> int:
        return int((self.replacement_info or {}).get("deleted_assets", 0) or 0)

    def _replacement_deleted_vectors(self) -> int:
        return int((self.replacement_info or {}).get("deleted_vectors", 0) or 0)

    def format_ingestion_success_message(self, file_name: str) -> str:
        """User-facing summary after upload ingest (matches prior Streamlit copy)."""
        type_counts = self.content_type_counts()
        asset_count = len(self.raw_assets)
        da = self._replacement_deleted_assets()
        dv = self._replacement_deleted_vectors()
        if da or dv:
            return (
                f"{file_name}: replaced previous ingestion "
                f"({da} SQLite asset(s) removed, {dv} FAISS vector(s) removed), "
                f"then processed {asset_count} multimodal asset(s) {type_counts}"
            )
        return f"{file_name}: processed {asset_count} multimodal asset(s) {type_counts}"

    def format_reindex_success_message(self, file_name: str) -> str:
        """User-facing summary after reindex (matches prior Streamlit copy)."""
        type_counts = self.content_type_counts()
        da = self._replacement_deleted_assets()
        dv = self._replacement_deleted_vectors()
        return (
            f"{file_name}: reindexed successfully "
            f"({da} SQLite asset(s) replaced, {dv} FAISS vector(s) replaced), "
            f"generated {len(self.raw_assets)} multimodal asset(s) {type_counts}."
        )

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

    def format_delete_summary(self, doc_name: str) -> str:
        """User-facing line after delete (matches prior Streamlit copy)."""
        return (
            f"{doc_name}: file deleted={self.file_deleted}, "
            f"SQLite assets removed={self.deleted_assets}, "
            f"FAISS vectors removed={self.deleted_vectors}."
        )

    def as_payload(self) -> dict:
        return {
            "source_file": self.source_file,
            "file_deleted": self.file_deleted,
            "deleted_vectors": self.deleted_vectors,
            "deleted_assets": self.deleted_assets,
        }
