"""Document extraction + summarization pipeline for ingestion use cases."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from domain.projects.buffered_document_upload import BufferedDocumentUpload
from domain.projects.project import Project


@runtime_checkable
class DocumentIngestionPort(Protocol):
    def ingest_uploaded_file(
        self, project: Project, uploaded_file: BufferedDocumentUpload
    ) -> tuple[Any, Any, Any]: ...

    def ingest_file_path(
        self,
        *,
        project: Project,
        file_path: Any,
        source_file: str,
    ) -> tuple[Any, Any, Any]: ...
