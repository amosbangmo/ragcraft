import unittest

from src.core.config import RetrievalConfig
from src.domain.query_intent import QueryIntent
from src.domain.retrieval_settings import RetrievalSettings
from src.infrastructure.adapters.rag.adaptive_retrieval_service import AdaptiveRetrievalService


class TestAdaptiveRetrievalService(unittest.TestCase):
    def setUp(self) -> None:
        self.config = RetrievalConfig(
            similarity_search_k=25,
            bm25_search_k=25,
            hybrid_search_k=25,
            bm25_k1=1.5,
            bm25_b=0.75,
            bm25_epsilon=0.25,
            rrf_k=60,
            hybrid_beta=0.5,
            max_prompt_assets=5,
            max_text_chars_per_asset=4000,
            max_table_chars_per_asset=4000,
            enable_query_rewrite=True,
            query_rewrite_max_history_messages=6,
            enable_hybrid_retrieval=True,
        )
        self.settings = RetrievalSettings.from_retrieval_config(self.config)
        self.svc = AdaptiveRetrievalService()

    def test_unknown_preserves_baseline(self) -> None:
        s = self.svc.choose_strategy(
            settings=self.settings,
            intent=QueryIntent.UNKNOWN,
            rewritten_query="anything",
        )
        self.assertEqual(s.k, 25)
        self.assertTrue(s.use_hybrid)
        self.assertTrue(s.apply_filters)

    def test_factual_disables_hybrid_and_lowers_k(self) -> None:
        s = self.svc.choose_strategy(
            settings=self.settings,
            intent=QueryIntent.FACTUAL,
            rewritten_query="What is the revenue in Q3?",
        )
        self.assertFalse(s.use_hybrid)
        self.assertLessEqual(s.k, 5)
        self.assertGreaterEqual(s.k, 3)
        self.assertFalse(s.apply_filters)

    def test_exploratory_enables_hybrid_and_higher_k(self) -> None:
        s = self.svc.choose_strategy(
            settings=self.settings,
            intent=QueryIntent.EXPLORATORY,
            rewritten_query="Give background and context on the strategy section",
        )
        self.assertTrue(s.use_hybrid)
        self.assertGreaterEqual(s.k, 8)
        self.assertTrue(s.apply_filters)

    def test_table_image_comparison_use_hybrid(self) -> None:
        for intent in (QueryIntent.TABLE, QueryIntent.IMAGE, QueryIntent.COMPARISON):
            with self.subTest(intent=intent):
                s = self.svc.choose_strategy(
                    settings=self.settings,
                    intent=intent,
                    rewritten_query="show the breakdown",
                )
                self.assertTrue(s.use_hybrid)
                self.assertTrue(s.apply_filters)

    def test_long_query_adjusts_k(self) -> None:
        long_q = " ".join(["word"] * 40)
        short = self.svc.choose_strategy(
            settings=self.settings,
            intent=QueryIntent.EXPLORATORY,
            rewritten_query="short query here",
        )
        long = self.svc.choose_strategy(
            settings=self.settings,
            intent=QueryIntent.EXPLORATORY,
            rewritten_query=long_q,
        )
        self.assertGreaterEqual(long.k, short.k)


if __name__ == "__main__":
    unittest.main()
