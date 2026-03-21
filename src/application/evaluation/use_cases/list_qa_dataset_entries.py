from __future__ import annotations

from src.domain.qa_dataset_entry import QADatasetEntry
from src.services.qa_dataset_service import QADatasetService


class ListQaDatasetEntriesUseCase:
    """List gold QA rows for a project in stable id order."""

    def __init__(self, *, qa_dataset_service: QADatasetService) -> None:
        self._qa = qa_dataset_service

    def execute(
        self,
        *,
        user_id: str,
        project_id: str,
    ) -> list[QADatasetEntry]:
        return self._qa.list_entries(
            user_id=user_id,
            project_id=project_id,
        )
