from __future__ import annotations

from src.domain.ports import QADatasetEntriesPort
from src.application.evaluation.dtos import DeleteQaDatasetEntryCommand


class DeleteQaDatasetEntryUseCase:
    """Delete a single QA row; raises if the row is not found in scope."""

    def __init__(self, *, qa_dataset: QADatasetEntriesPort) -> None:
        self._qa = qa_dataset

    def execute(self, command: DeleteQaDatasetEntryCommand) -> bool:
        return self._qa.delete_entry(
            entry_id=command.entry_id,
            user_id=command.user_id,
            project_id=command.project_id,
        )
