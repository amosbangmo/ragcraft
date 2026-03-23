"""Application read models for project / document listings (non-persistence rows)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectDocumentDetailRow:
    """One project root document with ingestion stats (replaces ad hoc dict rows)."""

    name: str
    project_id: str
    path: str
    size_bytes: int
    asset_count: int
    text_count: int
    table_count: int
    image_count: int
    latest_ingested_at: str | None
