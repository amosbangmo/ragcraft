import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.adapters.sqlite.project_settings_repository import SqliteProjectSettingsRepository
from src.domain.project_settings import ProjectSettings, ui_label_for_project_settings
from src.domain.retrieval_presets import RetrievalPreset
from src.infrastructure.persistence.db import init_app_db


class TestSqliteProjectSettingsRepository(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmpdir.name) / "project_settings_test.db"
        self._patcher = patch(
            "src.infrastructure.persistence.db.get_sqlite_db_path",
            return_value=self.db_path,
        )
        self._patcher.start()
        init_app_db()
        self.repo = SqliteProjectSettingsRepository()

    def tearDown(self) -> None:
        self._patcher.stop()
        self._tmpdir.cleanup()

    def test_load_missing_returns_balanced_default(self) -> None:
        ps = self.repo.load("u1", "p1")
        self.assertEqual(ps.retrieval_preset, RetrievalPreset.BALANCED.value)
        self.assertFalse(ps.retrieval_advanced)

    def test_save_and_load_roundtrip(self) -> None:
        self.repo.save(
            ProjectSettings(
                user_id="u1",
                project_id="p1",
                retrieval_preset=RetrievalPreset.PRECISE.value,
                retrieval_advanced=True,
                enable_query_rewrite=False,
                enable_hybrid_retrieval=True,
            )
        )
        ps = self.repo.load("u1", "p1")
        self.assertEqual(ps.retrieval_preset, RetrievalPreset.PRECISE.value)
        self.assertTrue(ps.retrieval_advanced)
        self.assertFalse(ps.enable_query_rewrite)
        self.assertTrue(ps.enable_hybrid_retrieval)

    def test_ui_label_for_saved_settings(self) -> None:
        self.repo.save(
            ProjectSettings(
                user_id="u1",
                project_id="p2",
                retrieval_preset=RetrievalPreset.EXPLORATORY.value,
                retrieval_advanced=False,
                enable_query_rewrite=True,
                enable_hybrid_retrieval=True,
            )
        )
        ps = self.repo.load("u1", "p2")
        self.assertEqual(ui_label_for_project_settings(ps), "Exploratory")


if __name__ == "__main__":
    unittest.main()
