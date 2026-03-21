import os
import unittest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from src.core.config import RETRIEVAL_CONFIG, RetrievalConfig
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


if __name__ == "__main__":
    unittest.main()
