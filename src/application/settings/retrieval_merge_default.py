"""Lazy default for :class:`~src.domain.ports.retrieval_preset_merge_port.RetrievalPresetMergePort` (composition-free callers)."""

from __future__ import annotations

from src.domain.ports.retrieval_preset_merge_port import RetrievalPresetMergePort


def default_retrieval_preset_merge_port() -> RetrievalPresetMergePort:
    from src.infrastructure.adapters.rag.retrieval_settings_service import RetrievalSettingsService

    return RetrievalSettingsService()
