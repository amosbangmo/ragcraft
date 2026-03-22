from __future__ import annotations

from dataclasses import dataclass

from src.domain.project_settings import ProjectSettings
from src.domain.retrieval_settings import RetrievalSettings


@dataclass(frozen=True)
class GetEffectiveRetrievalSettingsQuery:
    user_id: str
    project_id: str


@dataclass(frozen=True)
class UpdateProjectRetrievalSettingsCommand:
    """Persisted retrieval preferences for a project (preset semantics unchanged from UI)."""

    user_id: str
    project_id: str
    retrieval_preset: str
    retrieval_advanced: bool
    enable_query_rewrite: bool
    enable_hybrid_retrieval: bool


@dataclass(frozen=True)
class EffectiveRetrievalSettingsView:
    """Loaded preferences plus merged effective tuning used by RAG retrieval."""

    preferences: ProjectSettings
    effective_retrieval: RetrievalSettings
