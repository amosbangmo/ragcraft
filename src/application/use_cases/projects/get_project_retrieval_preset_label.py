from __future__ import annotations

from src.domain.ports import ProjectSettingsRepositoryPort
from src.domain.retrieval_presets import PRESET_UI_LABELS, parse_retrieval_preset


class GetProjectRetrievalPresetLabelUseCase:
    """Human-readable retrieval preset label for project listings."""

    def __init__(self, *, project_settings: ProjectSettingsRepositoryPort) -> None:
        self._settings = project_settings

    def execute(self, *, user_id: str, project_id: str) -> str:
        ps = self._settings.load(user_id, project_id)
        p = parse_retrieval_preset(ps.retrieval_preset)
        return PRESET_UI_LABELS[p]
