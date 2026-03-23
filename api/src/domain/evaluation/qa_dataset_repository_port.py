from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class QADatasetRepositoryPort(Protocol):
    """CRUD persistence for gold QA rows scoped by user and project."""

    def create_entry(
        self,
        *,
        user_id: str,
        project_id: str,
        question: str,
        expected_answer: str | None = None,
        expected_doc_ids: list[str] | None = None,
        expected_sources: list[str] | None = None,
    ) -> int: ...

    def list_entries(
        self,
        *,
        user_id: str,
        project_id: str,
    ) -> list[dict]: ...

    def get_entry_by_id(
        self,
        *,
        entry_id: int,
        user_id: str,
        project_id: str,
    ) -> dict | None: ...

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
    ) -> bool: ...

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
