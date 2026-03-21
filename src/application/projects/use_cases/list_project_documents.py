from __future__ import annotations

from src.services.project_service import ProjectService


class ListProjectDocumentsUseCase:
    """List source filenames stored at the root of a project directory (excludes index and logs)."""

    def __init__(self, *, project_service: ProjectService) -> None:
        self._project_service = project_service

    def execute(self, user_id: str, project_id: str) -> list[str]:
        return self._project_service.list_project_documents(user_id, project_id)
