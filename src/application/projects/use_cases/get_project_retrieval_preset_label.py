from __future__ import annotations

from src.services.project_settings_service import ProjectSettingsService


class GetProjectRetrievalPresetLabelUseCase:
    """Human-readable retrieval preset label for project listings."""

    def __init__(self, *, project_settings_service: ProjectSettingsService) -> None:
        self._settings = project_settings_service

    def execute(self, *, user_id: str, project_id: str) -> str:
        return self._settings.preset_label_for_project(user_id, project_id)
