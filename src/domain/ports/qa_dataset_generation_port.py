"""LLM-backed proposed QA entries for a project workspace."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class QaDatasetGenerationPort(Protocol):
    def generate_entries(
        self,
        *,
        user_id: str,
        project_id: str,
        num_questions: int,
        source_files: list[str] | None,
    ) -> list[dict[str, Any]]: ...
