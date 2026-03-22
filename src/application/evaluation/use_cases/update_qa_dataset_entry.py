from __future__ import annotations

from src.domain.qa_dataset_entry import QADatasetEntry
from src.domain.ports import QADatasetEntriesPort


class UpdateQaDatasetEntryUseCase:
    """Update an existing QA row scoped to user and project."""

    def __init__(self, *, qa_dataset: QADatasetEntriesPort) -> None:
        self._qa = qa_dataset

    def execute(
        self,
        *,
        entry_id: int,
        user_id: str,
        project_id: str,
        question: str,
        expected_answer: str | None = None,
        expected_doc_ids: list[str] | None = None,
        expected_sources: list[str] | None = None,
    ) -> QADatasetEntry:
        return self._qa.update_entry(
            entry_id=entry_id,
            user_id=user_id,
            project_id=project_id,
            question=question,
            expected_answer=expected_answer,
            expected_doc_ids=expected_doc_ids,
            expected_sources=expected_sources,
        )
