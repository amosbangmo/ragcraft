from __future__ import annotations

from domain.projects.project import Project
from domain.common.ports.project_workspace_port import ProjectWorkspacePort


class CreateProjectUseCase:
    """Ensure a project workspace directory exists for the given user and project id."""

    def __init__(self, *, project_service: ProjectWorkspacePort) -> None:
        self._project_service = project_service

    def execute(self, user_id: str, project_id: str) -> Project:
        return self._project_service.create_project(user_id, project_id)
