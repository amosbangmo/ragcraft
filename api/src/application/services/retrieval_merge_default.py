"""Lazy default for :class:`~domain.common.ports.retrieval_preset_merge_port.RetrievalPresetMergePort` (composition-free callers)."""

from __future__ import annotations

from application.services.retrieval_settings_tuner import RetrievalSettingsTuner
from domain.common.ports.retrieval_preset_merge_port import RetrievalPresetMergePort


def default_retrieval_preset_merge_port() -> RetrievalPresetMergePort:
    return RetrievalSettingsTuner()
