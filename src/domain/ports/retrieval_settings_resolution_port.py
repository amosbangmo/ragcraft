"""Merge persisted project preferences into effective :class:`~src.domain.retrieval_settings.RetrievalSettings`."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.domain.project_settings import ProjectSettings
from src.domain.retrieval_settings import RetrievalSettings


@runtime_checkable
class RetrievalSettingsResolutionPort(Protocol):
    def retrieval_settings_for_saved_project(self, settings: ProjectSettings) -> RetrievalSettings: ...
