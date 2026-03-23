"""LLM-proposed QA row before persistence (gold QA dataset generation)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProposedQaDatasetRow:
    question: str
    expected_answer: str | None
    expected_doc_ids: tuple[str, ...]
    expected_sources: tuple[str, ...]

    @classmethod
    def from_llm_dict(cls, row: dict[str, Any]) -> ProposedQaDatasetRow:
        q = (row.get("question") or "").strip()
        exp = row.get("expected_answer")
        exp_ans = None if exp is None else str(exp).strip() or None
        doc_ids = row.get("expected_doc_ids") or []
        sources = row.get("expected_sources") or []
        if not isinstance(doc_ids, list):
            doc_ids = []
        if not isinstance(sources, list):
            sources = []
        return cls(
            question=q,
            expected_answer=exp_ans,
            expected_doc_ids=tuple(str(x) for x in doc_ids if x is not None),
            expected_sources=tuple(str(x) for x in sources if x is not None),
        )
