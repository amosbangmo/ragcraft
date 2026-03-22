"""Lazy default for :class:`~src.domain.ports.retrieval_preset_merge_port.RetrievalPresetMergePort` (composition-free callers)."""

from __future__ import annotations

from src.application.settings.retrieval_settings_tuner import RetrievalSettingsTuner
from src.domain.ports.retrieval_preset_merge_port import RetrievalPresetMergePort


def default_retrieval_preset_merge_port() -> RetrievalPresetMergePort:
    return RetrievalSettingsTuner()
