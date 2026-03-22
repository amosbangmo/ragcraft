"""Project workspace paths and listings (user-scoped project directories)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.domain.project import Project


@runtime_checkable
class ProjectWorkspacePort(Protocol):
    def get_project(self, user_id: str, project_id: str) -> Project: ...

    def create_project(self, user_id: str, project_id: str) -> Project: ...

    def list_projects(self, user_id: str | None) -> list[str]: ...

    def list_project_documents(self, user_id: str, project_id: str) -> list[str]: ...
