import unittest

from src.application.settings.retrieval_settings_tuner import RetrievalSettingsTuner
from src.ui.retrieval_settings_panel import (
    PRESET_BALANCED,
    PRESET_EXPLORATORY,
    PRESET_PRECISE,
    build_ui_retrieval_settings,
    retrieval_settings_to_request_dict,
)


class TestRetrievalSettingsPanel(unittest.TestCase):
    def test_precise_shapes_k_and_toggles(self):
        svc = RetrievalSettingsTuner()
        s = build_ui_retrieval_settings(
            preset=PRESET_PRECISE,
            enable_query_rewrite=True,
            enable_hybrid_retrieval=False,
            service=svc,
        )
        self.assertTrue(s.enable_query_rewrite)
        self.assertFalse(s.enable_hybrid_retrieval)
        self.assertEqual(s.similarity_search_k, 8)
        self.assertEqual(s.bm25_search_k, 8)
        self.assertEqual(s.hybrid_search_k, 8)

    def test_balanced_preserves_default_k(self):
        svc = RetrievalSettingsTuner()
        base = svc.get_default()
        s = build_ui_retrieval_settings(
            preset=PRESET_BALANCED,
            enable_query_rewrite=True,
            enable_hybrid_retrieval=True,
            service=svc,
        )
        self.assertEqual(s.similarity_search_k, base.similarity_search_k)
        self.assertEqual(s.bm25_search_k, base.bm25_search_k)
        self.assertEqual(s.hybrid_search_k, base.hybrid_search_k)

    def test_exploratory_scales_k_and_toggles(self):
        svc = RetrievalSettingsTuner()
        base = svc.get_default()
        s = build_ui_retrieval_settings(
            preset=PRESET_EXPLORATORY,
            enable_query_rewrite=False,
            enable_hybrid_retrieval=True,
            service=svc,
        )
        self.assertFalse(s.enable_query_rewrite)
        self.assertTrue(s.enable_hybrid_retrieval)
        self.assertGreaterEqual(s.similarity_search_k, 30)
        self.assertGreaterEqual(s.similarity_search_k, base.similarity_search_k)

    def test_request_dict_merge_roundtrip_flags(self):
        svc = RetrievalSettingsTuner()
        s = build_ui_retrieval_settings(
            preset=PRESET_BALANCED,
            enable_query_rewrite=False,
            enable_hybrid_retrieval=True,
            service=svc,
        )
        d = retrieval_settings_to_request_dict(s)
        merged = svc.merge(svc.get_default(), d)
        self.assertEqual(merged.enable_query_rewrite, False)
        self.assertEqual(merged.enable_hybrid_retrieval, True)
