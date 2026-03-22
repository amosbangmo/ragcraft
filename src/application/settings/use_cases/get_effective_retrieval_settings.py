from __future__ import annotations

from src.application.settings.dtos import (
    EffectiveRetrievalSettingsView,
    GetEffectiveRetrievalSettingsQuery,
)
from src.domain.ports import ProjectSettingsRepositoryPort
from src.services.retrieval_settings_service import RetrievalSettingsService


class GetEffectiveRetrievalSettingsUseCase:
    """Load persisted project preferences and compute merged :class:`~src.domain.retrieval_settings.RetrievalSettings`."""

    def __init__(
        self,
        *,
        project_settings: ProjectSettingsRepositoryPort,
        retrieval_settings: RetrievalSettingsService,
    ) -> None:
        self._project_settings = project_settings
        self._retrieval = retrieval_settings

    def execute(self, query: GetEffectiveRetrievalSettingsQuery) -> EffectiveRetrievalSettingsView:
        ps = self._project_settings.load(query.user_id, query.project_id)
        effective = self._retrieval.retrieval_settings_for_saved_project(ps)
        return EffectiveRetrievalSettingsView(preferences=ps, effective_retrieval=effective)
