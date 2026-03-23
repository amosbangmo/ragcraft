from __future__ import annotations

from application.dto.settings import (
    EffectiveRetrievalSettingsView,
    GetEffectiveRetrievalSettingsQuery,
)
from domain.common.ports import ProjectSettingsRepositoryPort
from domain.common.ports.retrieval_settings_resolution_port import RetrievalSettingsResolutionPort


class GetEffectiveRetrievalSettingsUseCase:
    """Load persisted project preferences and compute merged :class:`~domain.retrieval_settings.RetrievalSettings`."""

    def __init__(
        self,
        *,
        project_settings: ProjectSettingsRepositoryPort,
        retrieval_settings: RetrievalSettingsResolutionPort,
    ) -> None:
        self._project_settings = project_settings
        self._retrieval = retrieval_settings

    def execute(self, query: GetEffectiveRetrievalSettingsQuery) -> EffectiveRetrievalSettingsView:
        ps = self._project_settings.load(query.user_id, query.project_id)
        effective = self._retrieval.retrieval_settings_for_saved_project(ps)
        return EffectiveRetrievalSettingsView(preferences=ps, effective_retrieval=effective)
