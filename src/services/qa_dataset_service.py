from src.domain.evaluation.qa_dataset_repository_port import QADatasetRepositoryPort
from src.domain.evaluation.qa_question_key import normalized_qa_question_key
from src.domain.qa_dataset_entry import QADatasetEntry
from src.infrastructure.persistence.sqlite.qa_dataset_repository import QADatasetRepository


class QADatasetService:
    """Implements :class:`~src.domain.ports.qa_dataset_entries_port.QADatasetEntriesPort` via SQLite."""
    def __init__(self, repository: QADatasetRepositoryPort | None = None):
        self.repository: QADatasetRepositoryPort = (
            repository if repository is not None else QADatasetRepository()
        )

    def create_entry(
        self,
        *,
        user_id: str,
        project_id: str,
        question: str,
        expected_answer: str | None = None,
        expected_doc_ids: list[str] | None = None,
        expected_sources: list[str] | None = None,
    ) -> QADatasetEntry:
        normalized_question = (question or "").strip()
        normalized_expected_answer = (expected_answer or "").strip() or None
        normalized_expected_doc_ids = self._normalize_string_list(expected_doc_ids)
        normalized_expected_sources = self._normalize_string_list(expected_sources)

        if not normalized_question:
            raise ValueError("Question is required.")

        entry_id = self.repository.create_entry(
            user_id=user_id,
            project_id=project_id,
            question=normalized_question,
            expected_answer=normalized_expected_answer,
            expected_doc_ids=normalized_expected_doc_ids,
            expected_sources=normalized_expected_sources,
        )

        created = self.repository.get_entry_by_id(
            entry_id=entry_id,
            user_id=user_id,
            project_id=project_id,
        )

        if created is None:
            raise RuntimeError("QA dataset entry was created but could not be reloaded.")

        return self._to_entry(created)

    def list_entries(
        self,
        *,
        user_id: str,
        project_id: str,
    ) -> list[QADatasetEntry]:
        rows = self.repository.list_entries(
            user_id=user_id,
            project_id=project_id,
        )
        return [self._to_entry(row) for row in rows]

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
    ) -> QADatasetEntry:
        normalized_question = (question or "").strip()
        normalized_expected_answer = (expected_answer or "").strip() or None
        normalized_expected_doc_ids = self._normalize_string_list(expected_doc_ids)
        normalized_expected_sources = self._normalize_string_list(expected_sources)

        if not normalized_question:
            raise ValueError("Question is required.")

        updated = self.repository.update_entry(
            entry_id=entry_id,
            user_id=user_id,
            project_id=project_id,
            question=normalized_question,
            expected_answer=normalized_expected_answer,
            expected_doc_ids=normalized_expected_doc_ids,
            expected_sources=normalized_expected_sources,
        )

        if not updated:
            raise ValueError("QA dataset entry not found.")

        refreshed = self.repository.get_entry_by_id(
            entry_id=entry_id,
            user_id=user_id,
            project_id=project_id,
        )

        if refreshed is None:
            raise RuntimeError("QA dataset entry was updated but could not be reloaded.")

        return self._to_entry(refreshed)

    def delete_entry(
        self,
        *,
        entry_id: int,
        user_id: str,
        project_id: str,
    ) -> bool:
        deleted = self.repository.delete_entry(
            entry_id=entry_id,
            user_id=user_id,
            project_id=project_id,
        )

        if not deleted:
            raise ValueError("QA dataset entry not found.")

        return True

    def delete_all_entries(
        self,
        *,
        user_id: str,
        project_id: str,
    ) -> int:
        return self.repository.delete_all_entries(
            user_id=user_id,
            project_id=project_id,
        )

    def normalized_question_key(self, question: str) -> str:
        return normalized_qa_question_key(question)

    def existing_question_keys(
        self,
        *,
        user_id: str,
        project_id: str,
    ) -> set[str]:
        entries = self.list_entries(
            user_id=user_id,
            project_id=project_id,
        )
        return {
            self.normalized_question_key(entry.question)
            for entry in entries
            if entry.question.strip()
        }

    def _normalize_string_list(self, values: list[str] | None) -> list[str]:
        if not values:
            return []

        normalized: list[str] = []
        seen: set[str] = set()

        for value in values:
            cleaned = (value or "").strip()
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            normalized.append(cleaned)

        return normalized

    def _to_entry(self, row: dict) -> QADatasetEntry:
        return QADatasetEntry(
            id=int(row["id"]),
            user_id=str(row["user_id"]),
            project_id=str(row["project_id"]),
            question=str(row["question"]),
            expected_answer=row.get("expected_answer"),
            expected_doc_ids=list(row.get("expected_doc_ids", [])),
            expected_sources=list(row.get("expected_sources", [])),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )
