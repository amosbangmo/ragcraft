"""LLM-backed proposed QA entries for a project workspace."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.domain.qa_dataset_proposal import ProposedQaDatasetRow


@runtime_checkable
class QaDatasetGenerationPort(Protocol):
    def generate_entries(
        self,
        *,
        user_id: str,
        project_id: str,
        num_questions: int,
        source_files: list[str] | None,
    ) -> list[ProposedQaDatasetRow]: ...
