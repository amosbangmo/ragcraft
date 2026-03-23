from __future__ import annotations

from domain.evaluation.qa_dataset_entry import QADatasetEntry
from domain.common.ports import QADatasetEntriesPort
from application.dto.evaluation import ListQaDatasetEntriesQuery


class ListQaDatasetEntriesUseCase:
    """List gold QA rows for a project in stable id order."""

    def __init__(self, *, qa_dataset: QADatasetEntriesPort) -> None:
        self._qa = qa_dataset

    def execute(self, query: ListQaDatasetEntriesQuery) -> list[QADatasetEntry]:
        return self._qa.list_entries(
            user_id=query.user_id,
            project_id=query.project_id,
        )
