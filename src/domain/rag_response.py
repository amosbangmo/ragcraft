from dataclasses import dataclass, field
from typing import Any


@dataclass
class RAGResponse:
    question: str
    answer: str
    source_documents: list[Any] = field(default_factory=list)   # docs FAISS (summaries)
    raw_assets: list[Any] = field(default_factory=list)         # assets SQLite rehydratés
    confidence: float = 0.0
