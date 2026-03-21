from __future__ import annotations

from src.services.project_service import ProjectService


class ListProjectsUseCase:
    """List project directory names for a user workspace."""

    def __init__(self, *, project_service: ProjectService) -> None:
        self._project_service = project_service

    def execute(self, user_id: str) -> list[str]:
        return self._project_service.list_projects(user_id)
