from __future__ import annotations

from src.services.qa_dataset_service import QADatasetService


class DeleteQaDatasetEntryUseCase:
    """Delete a single QA row; raises if the row is not found in scope."""

    def __init__(self, *, qa_dataset_service: QADatasetService) -> None:
        self._qa = qa_dataset_service

    def execute(
        self,
        *,
        entry_id: int,
        user_id: str,
        project_id: str,
    ) -> bool:
        return self._qa.delete_entry(
            entry_id=entry_id,
            user_id=user_id,
            project_id=project_id,
        )
