from dataclasses import dataclass, field
from typing import Any


@dataclass
class RAGResponse:
    question: str
    answer: str
    source_documents: list[Any] = field(default_factory=list)  # summaries retrieved from FAISS
    raw_assets: list[Any] = field(default_factory=list)        # rehydrated raw assets from SQLite
    confidence: float = 0.0
