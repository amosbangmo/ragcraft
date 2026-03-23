from __future__ import annotations

from application.dto.settings import UpdateProjectRetrievalSettingsCommand
from domain.common.ports import ProjectSettingsRepositoryPort
from domain.projects.project_settings import ProjectSettings
from domain.rag.retrieval_presets import parse_retrieval_preset


class UpdateProjectRetrievalSettingsUseCase:
    """Normalize preset string and persist project retrieval preferences."""

    def __init__(self, *, project_settings: ProjectSettingsRepositoryPort) -> None:
        self._repo = project_settings

    def execute(self, command: UpdateProjectRetrievalSettingsCommand) -> ProjectSettings:
        preset = parse_retrieval_preset(command.retrieval_preset).value
        ps = ProjectSettings(
            user_id=command.user_id,
            project_id=command.project_id,
            retrieval_preset=preset,
            retrieval_advanced=bool(command.retrieval_advanced),
            enable_query_rewrite=bool(command.enable_query_rewrite),
            enable_hybrid_retrieval=bool(command.enable_hybrid_retrieval),
        )
        self._repo.save(ps)
        return ps
