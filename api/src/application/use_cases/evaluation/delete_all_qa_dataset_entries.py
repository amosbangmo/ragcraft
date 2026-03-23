from __future__ import annotations

from application.dto.evaluation import DeleteAllQaDatasetEntriesCommand
from domain.common.ports import QADatasetEntriesPort


class DeleteAllQaDatasetEntriesUseCase:
    """Remove every gold QA row for a project scope; returns how many rows were deleted."""

    def __init__(self, *, qa_dataset: QADatasetEntriesPort) -> None:
        self._qa = qa_dataset

    def execute(self, command: DeleteAllQaDatasetEntriesCommand) -> int:
        return self._qa.delete_all_entries(
            user_id=command.user_id,
            project_id=command.project_id,
        )
