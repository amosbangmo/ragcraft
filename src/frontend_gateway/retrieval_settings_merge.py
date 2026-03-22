from __future__ import annotations

from typing import Any, Mapping, Protocol, runtime_checkable

from src.domain.retrieval_presets import RetrievalPreset
from src.domain.retrieval_settings import RetrievalSettings
from src.backend.retrieval_settings_service import RetrievalSettingsService


@runtime_checkable
class RetrievalPresetMergePort(Protocol):
    def from_preset(self, preset: str | RetrievalPreset) -> RetrievalSettings: ...

    def merge(self, base: RetrievalSettings, overrides: Mapping[str, Any]) -> RetrievalSettings: ...


def default_retrieval_preset_merge_port() -> RetrievalPresetMergePort:
    return RetrievalSettingsService()
