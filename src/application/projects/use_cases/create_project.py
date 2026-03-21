from __future__ import annotations

from src.domain.project import Project
from src.services.project_service import ProjectService


class CreateProjectUseCase:
    """Ensure a project workspace directory exists for the given user and project id."""

    def __init__(self, *, project_service: ProjectService) -> None:
        self._project_service = project_service

    def execute(self, user_id: str, project_id: str) -> Project:
        return self._project_service.create_project(user_id, project_id)
