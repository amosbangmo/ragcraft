import unittest

from components.shared.retrieval_dashboard import (
    compute_retrieval_dashboard_metrics,
    distribution_buckets,
)


class TestRetrievalDashboard(unittest.TestCase):
    def test_compute_metrics_empty(self):
        m = compute_retrieval_dashboard_metrics([])
        self.assertEqual(m["total_queries"], 0)
        self.assertIsNone(m["avg_latency_ms"])
        self.assertIsNone(m["avg_confidence"])
        self.assertIsNone(m["hybrid_usage_rate"])

    def test_compute_metrics_averages_and_hybrid_rate(self):
        logs = [
            {"latency_ms": 100, "confidence": 0.5, "hybrid_retrieval_enabled": True},
            {"latency_ms": 200, "confidence": 0.7, "hybrid_retrieval_enabled": False},
        ]
        m = compute_retrieval_dashboard_metrics(logs)
        self.assertEqual(m["total_queries"], 2)
        self.assertAlmostEqual(m["avg_latency_ms"], 150.0)
        self.assertAlmostEqual(m["avg_confidence"], 0.6)
        self.assertAlmostEqual(m["hybrid_usage_rate"], 0.5)
        self.assertIsNotNone(m["avg_latency_hybrid_ms"])
        self.assertIsNotNone(m["avg_latency_faiss_ms"])

    def test_distribution_buckets_single_value(self):
        edges, counts = distribution_buckets([3.0, 3.0, 3.0], bin_count=5)
        self.assertEqual(edges, [3.0])
        self.assertEqual(counts, [3])


if __name__ == "__main__":
    unittest.main()
