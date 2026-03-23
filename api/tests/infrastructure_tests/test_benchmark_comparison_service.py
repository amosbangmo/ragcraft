import unittest

from infrastructure.evaluation.benchmark_comparison_service import BenchmarkComparisonService


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

    def test_compare_failure_counts_sorted_by_abs_delta(self) -> None:
        fa = {"counts": {"retrieval_failure": 2, "judge_failure": 1}}
        fb = {"counts": {"retrieval_failure": 5, "hallucination": 1, "judge_failure": 1}}
        out = self.svc.compare_failure_counts(fa, fb)
        by_t = {r["failure_type"]: r for r in out}
        self.assertEqual(by_t["retrieval_failure"]["delta"], 3)
        self.assertEqual(by_t["hallucination"]["delta"], 1)
        self.assertEqual(by_t["judge_failure"]["delta"], 0)
        deltas = [abs(int(r["delta"])) for r in out]
        self.assertEqual(deltas, sorted(deltas, reverse=True))

    def test_lower_is_better_improved_when_b_lower(self) -> None:
        a = {"avg_latency_ms": 120.0, "pipeline_failure_rate": 0.2, "hallucination_rate": 0.1}
        b = {"avg_latency_ms": 90.0, "pipeline_failure_rate": 0.05, "hallucination_rate": 0.02}
        rows = self.svc.compare(a, b)
        by_m = {r["metric"]: r for r in rows}
        self.assertEqual(by_m["avg_latency_ms"]["direction"], "improved")
        self.assertEqual(by_m["pipeline_failure_rate"]["direction"], "improved")
        self.assertEqual(by_m["hallucination_rate"]["direction"], "improved")

    def test_lower_is_better_regressed_when_b_higher(self) -> None:
        a = {"avg_latency_ms": 50.0, "hallucination_rate": 0.01}
        b = {"avg_latency_ms": 80.0, "hallucination_rate": 0.08}
        rows = self.svc.compare(a, b)
        by_m = {r["metric"]: r for r in rows}
        self.assertEqual(by_m["avg_latency_ms"]["direction"], "regressed")
        self.assertEqual(by_m["hallucination_rate"]["direction"], "regressed")

    def test_critical_regression_includes_avg_answer_correctness(self) -> None:
        a = {"avg_answer_correctness": 0.9}
        b = {"avg_answer_correctness": 0.83}
        rows = self.svc.compare(a, b)
        self.assertEqual(rows[0]["direction"], "critical_regression")

    def test_lower_is_better_neutral_when_equal(self) -> None:
        a = {"avg_latency_ms": 50.0, "hallucination_rate": 0.1}
        b = {"avg_latency_ms": 50.0, "hallucination_rate": 0.1}
        rows = self.svc.compare(a, b)
        self.assertTrue(all(r["direction"] == "neutral" for r in rows))

    def test_higher_is_better_neutral_when_equal(self) -> None:
        a = {"avg_recall_at_k": 0.7}
        b = {"avg_recall_at_k": 0.7}
        rows = self.svc.compare(a, b)
        self.assertEqual(rows[0]["direction"], "neutral")

    def test_pipeline_failure_rate_lower_is_better(self) -> None:
        a = {"pipeline_failure_rate": 0.2}
        b = {"pipeline_failure_rate": 0.05}
        rows = self.svc.compare(a, b)
        self.assertEqual(rows[0]["direction"], "improved")
        self.assertEqual(rows[0]["delta"], -0.15)


if __name__ == "__main__":
    unittest.main()
