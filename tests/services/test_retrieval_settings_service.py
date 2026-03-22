import os
import unittest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from src.core.config import RETRIEVAL_CONFIG, RetrievalConfig
from unittest.mock import MagicMock

from src.domain.project_settings import ProjectSettings
from src.domain.retrieval_presets import PRECISE_SEARCH_K, RetrievalPreset
from src.domain.retrieval_settings import RetrievalSettings
from src.services.retrieval_settings_service import RetrievalSettingsService


class TestRetrievalSettingsService(unittest.TestCase):
    def test_get_default_matches_retrieval_config(self) -> None:
        svc = RetrievalSettingsService()
        d = svc.get_default()
        ref = RetrievalSettings.from_retrieval_config(RETRIEVAL_CONFIG)
        self.assertEqual(d, ref)

    def test_merge_overrides_subset(self) -> None:
        svc = RetrievalSettingsService()
        base = svc.get_default()
        merged = svc.merge(base, {"similarity_search_k": 7, "max_prompt_assets": 3})
        self.assertEqual(merged.similarity_search_k, 7)
        self.assertEqual(merged.max_prompt_assets, 3)
        self.assertEqual(merged.bm25_search_k, base.bm25_search_k)

    def test_merge_unknown_key_raises(self) -> None:
        svc = RetrievalSettingsService()
        base = svc.get_default()
        with self.assertRaises(ValueError):
            svc.merge(base, {"not_a_real_field": 1})

    def test_validate_rejects_bad_k(self) -> None:
        svc = RetrievalSettingsService()
        base = svc.get_default()
        bad = RetrievalSettings.from_retrieval_config(
            RetrievalConfig(similarity_search_k=0),
        )
        with self.assertRaises(ValueError):
            svc.validate(bad)

    def test_from_preset_balanced_sets_rewrite_and_hybrid(self) -> None:
        svc = RetrievalSettingsService()
        base = svc.get_default()
        s = svc.from_preset(RetrievalPreset.BALANCED)
        self.assertTrue(s.enable_query_rewrite)
        self.assertTrue(s.enable_hybrid_retrieval)
        self.assertEqual(s.similarity_search_k, base.similarity_search_k)

    def test_from_preset_precise_low_k_no_hybrid(self) -> None:
        svc = RetrievalSettingsService()
        s = svc.from_preset("precise")
        self.assertTrue(s.enable_query_rewrite)
        self.assertFalse(s.enable_hybrid_retrieval)
        self.assertEqual(s.similarity_search_k, PRECISE_SEARCH_K)
        self.assertEqual(s.bm25_search_k, PRECISE_SEARCH_K)
        self.assertEqual(s.hybrid_search_k, PRECISE_SEARCH_K)

    def test_from_preset_exploratory_high_k_no_rewrite(self) -> None:
        svc = RetrievalSettingsService()
        base = svc.get_default()
        s = svc.from_preset(RetrievalPreset.EXPLORATORY)
        self.assertFalse(s.enable_query_rewrite)
        self.assertTrue(s.enable_hybrid_retrieval)
        self.assertGreaterEqual(s.similarity_search_k, 30)
        self.assertGreaterEqual(s.similarity_search_k, base.similarity_search_k)

    def test_from_project_without_service_matches_get_default(self) -> None:
        svc = RetrievalSettingsService()
        s = svc.from_project("any", "project")
        self.assertEqual(s, svc.get_default())

    def test_from_project_uses_project_settings_repository(self) -> None:
        repo = MagicMock()
        repo.load.return_value = ProjectSettings(
            user_id="u",
            project_id="p",
            retrieval_preset=RetrievalPreset.PRECISE.value,
            retrieval_advanced=False,
            enable_query_rewrite=True,
            enable_hybrid_retrieval=False,
        )
        svc = RetrievalSettingsService(project_settings_repository=repo)
        s = svc.from_project("u", "p")
        repo.load.assert_called_once_with("u", "p")
        self.assertFalse(s.enable_hybrid_retrieval)
        self.assertEqual(s.similarity_search_k, PRECISE_SEARCH_K)

    def test_retrieval_settings_for_saved_project_advanced_merges_toggles(self) -> None:
        svc = RetrievalSettingsService()
        ps = ProjectSettings(
            user_id="u",
            project_id="p",
            retrieval_preset=RetrievalPreset.BALANCED.value,
            retrieval_advanced=True,
            enable_query_rewrite=False,
            enable_hybrid_retrieval=False,
        )
        s = svc.retrieval_settings_for_saved_project(ps)
        self.assertFalse(s.enable_query_rewrite)
        self.assertFalse(s.enable_hybrid_retrieval)


if __name__ == "__main__":
    unittest.main()
