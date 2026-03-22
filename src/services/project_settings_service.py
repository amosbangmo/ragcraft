from __future__ import annotations

from datetime import datetime, timezone

from src.domain.project_settings import ProjectSettings
from src.domain.retrieval_presets import PRESET_UI_LABELS, RetrievalPreset, parse_retrieval_preset
from src.infrastructure.persistence.db import get_connection


class ProjectSettingsService:
    """SQLite-backed :class:`~src.domain.shared.project_settings_repository_port.ProjectSettingsRepositoryPort`."""

    @staticmethod
    def default_for(user_id: str, project_id: str) -> ProjectSettings:
        return ProjectSettings(
            user_id=user_id,
            project_id=project_id,
            retrieval_preset=RetrievalPreset.BALANCED.value,
            retrieval_advanced=False,
            enable_query_rewrite=True,
            enable_hybrid_retrieval=True,
        )

    def load(self, user_id: str, project_id: str) -> ProjectSettings:
        conn = get_connection()
        row = conn.execute(
            """
            SELECT retrieval_preset, retrieval_advanced, enable_query_rewrite, enable_hybrid_retrieval
            FROM project_retrieval_settings
            WHERE user_id = ? AND project_id = ?
            """,
            (user_id, project_id),
        ).fetchone()
        conn.close()

        if row is None:
            return self.default_for(user_id, project_id)

        preset = parse_retrieval_preset(row["retrieval_preset"]).value
        advanced = bool(row["retrieval_advanced"])
        return ProjectSettings(
            user_id=user_id,
            project_id=project_id,
            retrieval_preset=preset,
            retrieval_advanced=advanced,
            enable_query_rewrite=bool(row["enable_query_rewrite"]),
            enable_hybrid_retrieval=bool(row["enable_hybrid_retrieval"]),
        )

    def save(self, settings: ProjectSettings) -> None:
        preset = parse_retrieval_preset(settings.retrieval_preset).value
        conn = get_connection()
        conn.execute(
            """
            INSERT INTO project_retrieval_settings (
                user_id,
                project_id,
                retrieval_preset,
                retrieval_advanced,
                enable_query_rewrite,
                enable_hybrid_retrieval,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, project_id) DO UPDATE SET
                retrieval_preset = excluded.retrieval_preset,
                retrieval_advanced = excluded.retrieval_advanced,
                enable_query_rewrite = excluded.enable_query_rewrite,
                enable_hybrid_retrieval = excluded.enable_hybrid_retrieval,
                updated_at = excluded.updated_at
            """,
            (
                settings.user_id,
                settings.project_id,
                preset,
                1 if settings.retrieval_advanced else 0,
                1 if settings.enable_query_rewrite else 0,
                1 if settings.enable_hybrid_retrieval else 0,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
        conn.close()

    def preset_label_for_project(self, user_id: str, project_id: str) -> str:
        """Human-readable preset name for listings (e.g. projects page)."""
        ps = self.load(user_id, project_id)
        p = parse_retrieval_preset(ps.retrieval_preset)
        return PRESET_UI_LABELS[p]
