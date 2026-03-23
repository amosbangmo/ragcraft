from __future__ import annotations

from typing import Protocol, runtime_checkable

from domain.projects.project_settings import ProjectSettings


@runtime_checkable
class ProjectSettingsRepositoryPort(Protocol):
    """Load and persist per-project retrieval preferences."""

    def load(self, user_id: str, project_id: str) -> ProjectSettings: ...

    def save(self, settings: ProjectSettings) -> None: ...
