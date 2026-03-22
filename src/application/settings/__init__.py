"""
Project-scoped retrieval preferences and effective retrieval tuning (merged presets + overrides).

Use cases live in ``use_cases``; DTOs in ``dtos``. Persistence is the
:class:`~src.domain.shared.project_settings_repository_port.ProjectSettingsRepositoryPort`
(``ProjectSettingsService`` in infrastructure).
"""

from __future__ import annotations

from . import dtos

__all__ = ["dtos"]
