import unittest

from src.services.benchmark_comparison_service import BenchmarkComparisonService


class TestBenchmarkComparisonService(unittest.TestCase):
    def setUp(self) -> None:
        self.svc = BenchmarkComparisonService()

    def test_compare_delta_and_direction(self) -> None:
        a = {"avg_recall_at_k": 0.4, "avg_answer_f1": 0.8}
        b = {"avg_recall_at_k": 0.6, "avg_answer_f1": 0.7}
        rows = self.svc.compare(a, b)
        by_m = {r["metric"]: r for r in rows}
        self.assertEqual(by_m["avg_recall_at_k"]["direction"], "improved")
        self.assertEqual(by_m["avg_answer_f1"]["direction"], "critical_regression")

    def test_critical_regression(self) -> None:
        a = {"avg_answer_f1": 0.9}
        b = {"avg_answer_f1": 0.8}
        rows = self.svc.compare(a, b)
        self.assertEqual(rows[0]["direction"], "critical_regression")

    def test_skips_non_numeric(self) -> None:
        a = {"total_entries": "5", "avg_recall_at_k": 1.0}
        b = {"total_entries": "5", "avg_recall_at_k": 1.0}
        rows = self.svc.compare(a, b)
        self.assertEqual(len(rows), 1)

    def test_compare_failure_counts(self) -> None:
        fa = {"counts": {"retrieval_failure": 2}}
        fb = {"counts": {"retrieval_failure": 5, "hallucination": 1}}
        out = self.svc.compare_failure_counts(fa, fb)
        by_t = {r["failure_type"]: r for r in out}
        self.assertEqual(by_t["retrieval_failure"]["delta"], 3)
        self.assertEqual(by_t["hallucination"]["run_a"], 0)


if __name__ == "__main__":
    unittest.main()
