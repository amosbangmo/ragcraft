"""
Project-scoped retrieval preferences and effective retrieval tuning (merged presets + overrides).

Use cases live in ``application.use_cases.settings``; DTOs in ``dtos``. Persistence is the
:class:`~domain.common.shared.project_settings_repository_port.ProjectSettingsRepositoryPort`
(typically :class:`~infrastructure.persistence.sqlite.project_settings_repository.SqliteProjectSettingsRepository`).
"""

from __future__ import annotations

from . import dtos

__all__ = ["dtos"]
