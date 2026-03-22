import unittest

from src.infrastructure.adapters.rag.confidence_service import ConfidenceService


class TestConfidenceService(unittest.TestCase):
    def setUp(self):
        self.svc = ConfidenceService()

    def test_empty_assets_returns_zero(self):
        self.assertEqual(self.svc.compute_confidence(reranked_raw_assets=[]), 0.0)

    def test_missing_scores_returns_zero(self):
        assets = [{"doc_id": "d1", "metadata": {}}]
        self.assertEqual(self.svc.compute_confidence(reranked_raw_assets=assets), 0.0)

    def test_one_strong_asset_is_mid_to_high_band(self):
        assets = [
            {
                "doc_id": "d1",
                "metadata": {"rerank_score": 8.0},
            }
        ]
        c = self.svc.compute_confidence(reranked_raw_assets=assets)
        self.assertGreaterEqual(c, 0.55)
        self.assertLessEqual(c, 1.0)

    def test_multiple_strong_consistent_assets_beats_single_when_top_similar(self):
        one = [{"doc_id": "a", "metadata": {"rerank_score": 5.0}}]
        many = [
            {"doc_id": "a", "metadata": {"rerank_score": 5.0}},
            {"doc_id": "b", "metadata": {"rerank_score": 4.9}},
            {"doc_id": "c", "metadata": {"rerank_score": 4.8}},
        ]
        c1 = self.svc.compute_confidence(reranked_raw_assets=one)
        c2 = self.svc.compute_confidence(reranked_raw_assets=many)
        self.assertGreater(c2, c1)

    def test_weak_assets_lower_than_strong(self):
        weak = [
            {"doc_id": "a", "metadata": {"rerank_score": -4.0}},
            {"doc_id": "b", "metadata": {"rerank_score": -4.2}},
        ]
        strong = [
            {"doc_id": "a", "metadata": {"rerank_score": 6.0}},
            {"doc_id": "b", "metadata": {"rerank_score": 5.5}},
        ]
        self.assertGreater(
            self.svc.compute_confidence(reranked_raw_assets=strong),
            self.svc.compute_confidence(reranked_raw_assets=weak),
        )

    def test_large_gap_between_top_two_increases_confidence(self):
        tight = [
            {"doc_id": "a", "metadata": {"rerank_score": 3.0}},
            {"doc_id": "b", "metadata": {"rerank_score": 2.99}},
        ]
        wide = [
            {"doc_id": "a", "metadata": {"rerank_score": 6.0}},
            {"doc_id": "b", "metadata": {"rerank_score": 0.0}},
        ]
        self.assertGreater(
            self.svc.compute_confidence(reranked_raw_assets=wide),
            self.svc.compute_confidence(reranked_raw_assets=tight),
        )

    def test_result_clamped_and_rounded(self):
        assets = [{"doc_id": "x", "metadata": {"rerank_score": 20.0}}]
        c = self.svc.compute_confidence(reranked_raw_assets=assets)
        self.assertEqual(c, round(c, 2))
        self.assertGreaterEqual(c, 0.0)
        self.assertLessEqual(c, 1.0)

    def test_more_source_diversity_raises_support_when_scores_match(self):
        base_meta = {"rerank_score": 4.0}
        same_file = [
            {"doc_id": "a", "source_file": "doc.pdf", "metadata": base_meta},
            {"doc_id": "b", "source_file": "doc.pdf", "metadata": {"rerank_score": 3.9}},
        ]
        mixed_files = [
            {"doc_id": "a", "source_file": "a.pdf", "metadata": base_meta},
            {"doc_id": "b", "source_file": "b.pdf", "metadata": {"rerank_score": 3.9}},
        ]
        self.assertGreater(
            self.svc.compute_confidence(reranked_raw_assets=mixed_files),
            self.svc.compute_confidence(reranked_raw_assets=same_file),
        )


if __name__ == "__main__":
    unittest.main()
