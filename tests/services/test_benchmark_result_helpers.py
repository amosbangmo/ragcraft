import unittest

from tests.fixtures.benchmark_results import make_benchmark_result
from tests.quality.benchmark_regression_checks import (
    BenchmarkRegressionThresholds,
    collect_benchmark_regression_violations,
)


class TestBenchmarkRegressionSummaryParsing(unittest.TestCase):
    """Guards tolerant parsing of summary values (strings, missing keys)."""

    def test_missing_metric_keys_treated_as_zero_for_minimum_checks(self):
        result = make_benchmark_result(
            summary_overrides={
                "successful_queries": 1,
            }
        )
        # Drop keys entirely to simulate partial / legacy payloads.
        result.summary.data.pop("avg_doc_id_recall", None)
        result.summary.data.pop("avg_answer_f1", None)
        result.summary.data.pop("avg_citation_source_f1", None)

        thresholds = BenchmarkRegressionThresholds(
            min_avg_doc_id_recall=0.01,
            min_avg_answer_f1=0.01,
            min_avg_citation_source_f1=0.01,
        )
        violations = collect_benchmark_regression_violations(result, thresholds)
        self.assertEqual(len(violations), 3)

    def test_numeric_strings_are_accepted(self):
        result = make_benchmark_result(
            summary_overrides={
                "successful_queries": "4",
                "avg_doc_id_recall": "0.75",
                "avg_answer_f1": "0.5",
                "avg_citation_source_f1": "0.25",
            }
        )
        thresholds = BenchmarkRegressionThresholds(
            min_successful_queries=4,
            min_avg_doc_id_recall=0.75,
            min_avg_answer_f1=0.5,
            min_avg_citation_source_f1=0.25,
        )
        self.assertEqual(collect_benchmark_regression_violations(result, thresholds), [])
