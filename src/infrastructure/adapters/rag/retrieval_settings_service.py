"""Composition-facing name for :class:`~src.application.settings.retrieval_settings_tuner.RetrievalSettingsTuner`."""

from __future__ import annotations

from src.application.settings.retrieval_settings_tuner import RetrievalSettingsTuner


class RetrievalSettingsService(RetrievalSettingsTuner):
    """Wired at the composition root; logic lives in the application layer."""

    __slots__ = ()
