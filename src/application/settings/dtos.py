from __future__ import annotations

from dataclasses import dataclass

from src.domain.project_settings import ProjectSettings
from src.domain.retrieval_settings import RetrievalSettings


@dataclass(frozen=True)
class GetEffectiveRetrievalSettingsQuery:
    """Input for loading saved project preferences and computing merged retrieval tuning."""

    user_id: str
    project_id: str


@dataclass(frozen=True)
class UpdateProjectRetrievalSettingsCommand:
    """
    Persisted retrieval preferences for a project.

    Preset strings are normalized via :func:`~src.domain.retrieval_presets.parse_retrieval_preset`
    in the update use case; invalid values surface as :class:`ValueError`.
    """

    user_id: str
    project_id: str
    retrieval_preset: str
    retrieval_advanced: bool
    enable_query_rewrite: bool
    enable_hybrid_retrieval: bool


@dataclass(frozen=True)
class EffectiveRetrievalSettingsView:
    """
    Application read model: saved :class:`~src.domain.project_settings.ProjectSettings` plus
    merged :class:`~src.domain.retrieval_settings.RetrievalSettings` used by RAG.

    HTTP responses map this through :class:`~src.application.http.wire.EffectiveRetrievalSettingsWirePayload`.
    """

    preferences: ProjectSettings
    effective_retrieval: RetrievalSettings
