"""SQLite-backed multimodal asset row (typed alternative to ad-hoc dict payloads)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StoredMultimodalAsset:
    doc_id: str
    user_id: str
    project_id: str
    source_file: str
    content_type: str
    raw_content: str
    summary: str
    metadata: Mapping[str, Any]
    created_at: str | None

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> StoredMultimodalAsset:
        md = raw.get("metadata")
        meta: Mapping[str, Any] = md if isinstance(md, Mapping) else {}
        return cls(
            doc_id=str(raw.get("doc_id") or ""),
            user_id=str(raw.get("user_id") or ""),
            project_id=str(raw.get("project_id") or ""),
            source_file=str(raw.get("source_file") or ""),
            content_type=str(raw.get("content_type") or "unknown"),
            raw_content="" if raw.get("raw_content") is None else str(raw.get("raw_content")),
            summary="" if raw.get("summary") is None else str(raw.get("summary")),
            metadata=meta,
            created_at=None if raw.get("created_at") is None else str(raw.get("created_at")),
        )

    def upsert_kwargs(self) -> dict[str, Any]:
        """Keyword args for :meth:`~domain.projects.documents.asset_repository_port.AssetRepositoryPort.upsert_asset`."""
        return {
            "doc_id": self.doc_id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "source_file": self.source_file,
            "content_type": self.content_type,
            "raw_content": self.raw_content,
            "summary": self.summary,
            "metadata": dict(self.metadata),
        }
