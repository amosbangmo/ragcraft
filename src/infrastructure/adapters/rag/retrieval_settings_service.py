"""
Composition-facing name for :class:`~src.application.settings.retrieval_settings_tuner.RetrievalSettingsTuner`.

**Architecture:** This module is the only file under ``src/infrastructure/adapters`` allowed to import
``src.application`` (see ``tests/architecture/test_adapter_application_imports.py``): it is a typed
alias/subclass of application retrieval tuning, not orchestration.
"""

from __future__ import annotations

from src.application.settings.retrieval_settings_tuner import RetrievalSettingsTuner


class RetrievalSettingsService(RetrievalSettingsTuner):
    """Wired at the composition root; logic lives in the application layer."""

    __slots__ = ()
