from __future__ import annotations

from typing import Protocol, runtime_checkable

from domain.evaluation.qa_dataset_entry import QADatasetEntry


@runtime_checkable
class QADatasetEntriesPort(Protocol):
    """
    Gold QA dataset operations returning domain :class:`~domain.qa_dataset_entry.QADatasetEntry`.

    Implemented by :class:`~infrastructure.evaluation.qa_dataset_service.QADatasetService`, which delegates
    persistence to :class:`~domain.evaluation.qa_dataset_repository_port.QADatasetRepositoryPort`.
    """

    def create_entry(
        self,
        *,
        user_id: str,
        project_id: str,
        question: str,
        expected_answer: str | None = None,
        expected_doc_ids: list[str] | None = None,
        expected_sources: list[str] | None = None,
    ) -> QADatasetEntry: ...

    def list_entries(
        self,
        *,
        user_id: str,
        project_id: str,
    ) -> list[QADatasetEntry]: ...

    def update_entry(
        self,
        *,
        entry_id: int,
        user_id: str,
        project_id: str,
        question: str,
        expected_answer: str | None = None,
        expected_doc_ids: list[str] | None = None,
        expected_sources: list[str] | None = None,
    ) -> QADatasetEntry: ...

    def delete_entry(
        self,
        *,
        entry_id: int,
        user_id: str,
        project_id: str,
    ) -> bool: ...

    def delete_all_entries(
        self,
        *,
        user_id: str,
        project_id: str,
    ) -> int: ...

    def existing_question_keys(
        self,
        *,
        user_id: str,
        project_id: str,
    ) -> set[str]: ...
