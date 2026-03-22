from __future__ import annotations

from src.domain.ports.project_workspace_port import ProjectWorkspacePort


class ListProjectDocumentsUseCase:
    """List source filenames stored at the root of a project directory (excludes index and logs)."""

    def __init__(self, *, project_service: ProjectWorkspacePort) -> None:
        self._project_service = project_service

    def execute(self, user_id: str, project_id: str) -> list[str]:
        return self._project_service.list_project_documents(user_id, project_id)
