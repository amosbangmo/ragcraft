import unittest

from tests.fixtures.benchmark_results import make_benchmark_result
from tests.quality.benchmark_regression_checks import (
    BenchmarkRegressionThresholds,
    assert_benchmark_meets_thresholds,
    collect_benchmark_regression_violations,
)


class TestBenchmarkRegressionThresholds(unittest.TestCase):
    def test_passes_when_metrics_meet_minimums(self):
        result = make_benchmark_result(
            summary_overrides={
                "successful_queries": 3,
                "avg_recall_at_k": 0.85,
                "avg_answer_f1": 0.72,
                "avg_prompt_doc_id_f1": 0.61,
            }
        )
        thresholds = BenchmarkRegressionThresholds(
            min_successful_queries=3,
            min_avg_recall_at_k=0.8,
            min_avg_answer_f1=0.7,
            min_avg_prompt_doc_id_f1=0.6,
        )
        assert_benchmark_meets_thresholds(result, thresholds)
        self.assertEqual(
            collect_benchmark_regression_violations(result, thresholds),
            [],
        )

    def test_fails_when_any_metric_drops_below_minimum(self):
        result = make_benchmark_result(
            summary_overrides={
                "successful_queries": 2,
                "avg_recall_at_k": 0.5,
                "avg_answer_f1": 0.9,
                "avg_prompt_doc_id_f1": 0.9,
            }
        )
        thresholds = BenchmarkRegressionThresholds(
            min_successful_queries=3,
            min_avg_recall_at_k=0.8,
            min_avg_answer_f1=0.7,
            min_avg_prompt_doc_id_f1=0.6,
        )
        with self.assertRaises(AssertionError) as ctx:
            assert_benchmark_meets_thresholds(result, thresholds)
        message = str(ctx.exception)
        self.assertIn("successful_queries", message)
        self.assertIn("avg_recall_at_k", message)

    def test_groundedness_threshold_enforced_when_set(self):
        result = make_benchmark_result(
            summary_overrides={
                "successful_queries": 1,
                "avg_groundedness_score": 0.2,
            }
        )
        thresholds = BenchmarkRegressionThresholds(min_avg_groundedness_score=0.5)
        violations = collect_benchmark_regression_violations(result, thresholds)
        self.assertEqual(len(violations), 1)
        self.assertIn("avg_groundedness_score", violations[0])

    def test_prompt_doc_id_f1_threshold_enforced_when_set(self):
        result = make_benchmark_result(
            summary_overrides={
                "successful_queries": 1,
                "avg_prompt_doc_id_f1": 0.2,
            }
        )
        thresholds = BenchmarkRegressionThresholds(min_avg_prompt_doc_id_f1=0.5)
        violations = collect_benchmark_regression_violations(result, thresholds)
        self.assertEqual(len(violations), 1)
        self.assertIn("avg_prompt_doc_id_f1", violations[0])

    def test_answer_relevance_threshold_enforced_when_set(self):
        result = make_benchmark_result(
            summary_overrides={
                "successful_queries": 1,
                "avg_answer_relevance_score": 0.2,
            }
        )
        thresholds = BenchmarkRegressionThresholds(min_avg_answer_relevance_score=0.5)
        violations = collect_benchmark_regression_violations(result, thresholds)
        self.assertEqual(len(violations), 1)
        self.assertIn("avg_answer_relevance_score", violations[0])

    def test_unset_thresholds_are_not_enforced(self):
        result = make_benchmark_result(
            summary_overrides={
                "successful_queries": 0,
                "avg_recall_at_k": 0.0,
            }
        )
        thresholds = BenchmarkRegressionThresholds()
        assert_benchmark_meets_thresholds(result, thresholds)
