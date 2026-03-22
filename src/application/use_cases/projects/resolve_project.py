"""Resolve a user's project workspace (path + identity) for downstream use cases."""

from __future__ import annotations

from src.domain.project import Project
from src.infrastructure.adapters.workspace.project_service import ProjectService


class ResolveProjectUseCase:
    """Thin application entry for :meth:`~src.infrastructure.adapters.workspace.project_service.ProjectService.get_project`."""

    def __init__(self, *, project_service: ProjectService) -> None:
        self._projects = project_service

    def execute(self, user_id: str, project_id: str) -> Project:
        return self._projects.get_project(user_id, project_id)
