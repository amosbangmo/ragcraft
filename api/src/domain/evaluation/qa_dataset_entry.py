from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class QADatasetEntry:
    id: int
    user_id: str
    project_id: str
    question: str
    expected_answer: str | None = None
    expected_doc_ids: list[str] = field(default_factory=list)
    expected_sources: list[str] = field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "question": self.question,
            "expected_answer": self.expected_answer,
            "expected_doc_ids": list(self.expected_doc_ids),
            "expected_sources": list(self.expected_sources),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
