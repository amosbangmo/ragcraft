"""Summary-level retrieval unit (FAISS / BM25 hits) without LangChain types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SummaryRecallDocument:
    """Mirrors the shape Streamlit/API clients expect: ``page_content`` + ``metadata`` (e.g. ``doc_id``)."""

    page_content: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"page_content": self.page_content, "metadata": dict(self.metadata)}
