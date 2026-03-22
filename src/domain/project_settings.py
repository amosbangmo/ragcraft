from __future__ import annotations

from dataclasses import dataclass

from src.domain.retrieval_presets import PRESET_UI_LABELS, RetrievalPreset, parse_retrieval_preset


@dataclass(frozen=True)
class ProjectSettings:
    """Persisted retrieval preferences for a single user project workspace."""

    user_id: str
    project_id: str
    retrieval_preset: str
    retrieval_advanced: bool = False
    enable_query_rewrite: bool = True
    enable_hybrid_retrieval: bool = True


def default_project_settings(user_id: str, project_id: str) -> ProjectSettings:
    """Defaults used when no row exists (matches former ``ProjectSettingsService.default_for``)."""
    return ProjectSettings(
        user_id=user_id,
        project_id=project_id,
        retrieval_preset=RetrievalPreset.BALANCED.value,
        retrieval_advanced=False,
        enable_query_rewrite=True,
        enable_hybrid_retrieval=True,
    )


def ui_label_for_project_settings(ps: ProjectSettings) -> str:
    """Human-readable preset label for UI (e.g. projects list)."""
    return PRESET_UI_LABELS[parse_retrieval_preset(ps.retrieval_preset)]
