"""Resolve a user's project workspace (path + identity) for downstream use cases."""

from __future__ import annotations

from domain.projects.project import Project
from domain.common.ports.project_workspace_port import ProjectWorkspacePort


class ResolveProjectUseCase:
    """Thin application entry for workspace project resolution."""

    def __init__(self, *, project_service: ProjectWorkspacePort) -> None:
        self._projects = project_service

    def execute(self, user_id: str, project_id: str) -> Project:
        return self._projects.get_project(user_id, project_id)
