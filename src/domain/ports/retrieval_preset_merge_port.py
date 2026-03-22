"""Preset selection and field-level merge for retrieval settings (UI / HTTP helpers)."""

from __future__ import annotations

from typing import Any, Mapping, Protocol, runtime_checkable

from src.domain.retrieval_presets import RetrievalPreset
from src.domain.retrieval_settings import RetrievalSettings


@runtime_checkable
class RetrievalPresetMergePort(Protocol):
    def from_preset(self, preset: str | RetrievalPreset) -> RetrievalSettings: ...

    def merge(self, base: RetrievalSettings, overrides: Mapping[str, Any]) -> RetrievalSettings: ...
