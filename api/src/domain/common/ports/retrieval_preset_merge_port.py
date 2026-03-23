"""Preset selection and field-level merge for retrieval settings (UI / HTTP helpers)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from domain.rag.retrieval_presets import RetrievalPreset
from domain.rag.retrieval_settings import RetrievalSettings


@runtime_checkable
class RetrievalPresetMergePort(Protocol):
    def from_preset(self, preset: str | RetrievalPreset) -> RetrievalSettings: ...

    def merge(self, base: RetrievalSettings, overrides: Mapping[str, Any]) -> RetrievalSettings: ...
