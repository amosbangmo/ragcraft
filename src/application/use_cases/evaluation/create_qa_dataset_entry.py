from __future__ import annotations

from src.domain.ports import QADatasetEntriesPort
from src.domain.qa_dataset_entry import QADatasetEntry
from src.application.evaluation.dtos import CreateQaDatasetEntryCommand


class CreateQaDatasetEntryUseCase:
    """Create a gold QA row with normalized fields and required-question validation."""

    def __init__(self, *, qa_dataset: QADatasetEntriesPort) -> None:
        self._qa = qa_dataset

    def execute(self, command: CreateQaDatasetEntryCommand) -> QADatasetEntry:
        return self._qa.create_entry(
            user_id=command.user_id,
            project_id=command.project_id,
            question=command.question,
            expected_answer=command.expected_answer,
            expected_doc_ids=command.expected_doc_ids,
            expected_sources=command.expected_sources,
        )
