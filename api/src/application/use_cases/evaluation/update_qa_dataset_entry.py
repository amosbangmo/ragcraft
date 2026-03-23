from __future__ import annotations

from application.dto.evaluation import UpdateQaDatasetEntryCommand
from domain.common.ports import QADatasetEntriesPort
from domain.evaluation.qa_dataset_entry import QADatasetEntry


class UpdateQaDatasetEntryUseCase:
    """Update an existing QA row scoped to user and project."""

    def __init__(self, *, qa_dataset: QADatasetEntriesPort) -> None:
        self._qa = qa_dataset

    def execute(self, command: UpdateQaDatasetEntryCommand) -> QADatasetEntry:
        return self._qa.update_entry(
            entry_id=command.entry_id,
            user_id=command.user_id,
            project_id=command.project_id,
            question=command.question,
            expected_answer=command.expected_answer,
            expected_doc_ids=command.expected_doc_ids,
            expected_sources=command.expected_sources,
        )
