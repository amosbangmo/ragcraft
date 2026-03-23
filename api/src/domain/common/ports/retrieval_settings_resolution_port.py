"""Merge persisted project preferences into effective :class:`~domain.retrieval_settings.RetrievalSettings`."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from domain.projects.project_settings import ProjectSettings
from domain.rag.retrieval_settings import RetrievalSettings


@runtime_checkable
class RetrievalSettingsResolutionPort(Protocol):
    def retrieval_settings_for_saved_project(self, settings: ProjectSettings) -> RetrievalSettings: ...
