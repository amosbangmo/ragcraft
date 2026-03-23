import unittest

from domain.evaluation.benchmark_result import BenchmarkResult, BenchmarkRow, BenchmarkSummary, coerce_benchmark_result
from fixtures.benchmark_results import make_benchmark_result
from e2e.benchmark_regression_checks import (
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
        result.summary.data.pop("avg_recall_at_k", None)
        result.summary.data.pop("avg_answer_f1", None)
        result.summary.data.pop("avg_prompt_doc_id_f1", None)

        thresholds = BenchmarkRegressionThresholds(
            min_avg_recall_at_k=0.01,
            min_avg_answer_f1=0.01,
            min_avg_prompt_doc_id_f1=0.01,
        )
        violations = collect_benchmark_regression_violations(result, thresholds)
        self.assertEqual(len(violations), 3)

    def test_numeric_strings_are_accepted(self):
        result = make_benchmark_result(
            summary_overrides={
                "successful_queries": "4",
                "avg_recall_at_k": "0.75",
                "avg_answer_f1": "0.5",
                "avg_prompt_doc_id_f1": "0.25",
            }
        )
        thresholds = BenchmarkRegressionThresholds(
            min_successful_queries=4,
            min_avg_recall_at_k=0.75,
            min_avg_answer_f1=0.5,
            min_avg_prompt_doc_id_f1=0.25,
        )
        self.assertEqual(collect_benchmark_regression_violations(result, thresholds), [])


class TestBenchmarkResultSessionRoundTrip(unittest.TestCase):
    def test_from_plain_dict_round_trips_to_dict(self):
        row = BenchmarkRow(entry_id=7, question="What?", data={"confidence": 0.5, "recall_at_k": 0.8})
        correlations = {"available": True, "pairwise": {"confidence_vs_latency_ms": 0.25}}
        failures = {"failed_row_count": 1, "counts": {"retrieval_failure": 1}}
        multimodal_metrics = {"table_usage_rate": 0.25, "has_multimodal_assets": True}
        auto_debug = [{"title": "T", "description": "D"}]
        original = BenchmarkResult(
            summary=BenchmarkSummary(data={"avg_recall_at_k": 0.9}),
            rows=[row],
            correlations=correlations,
            failures=failures,
            multimodal_metrics=multimodal_metrics,
            auto_debug=auto_debug,
            run_id="abc123runid",
        )
        restored = BenchmarkResult.from_plain_dict(original.to_dict())
        self.assertEqual(restored.summary.data, original.summary.data)
        self.assertEqual(len(restored.rows), 1)
        self.assertEqual(restored.rows[0].entry_id, 7)
        self.assertEqual(restored.rows[0].question, "What?")
        self.assertEqual(restored.rows[0].data["confidence"], 0.5)
        self.assertEqual(restored.rows[0].data["recall_at_k"], 0.8)
        self.assertEqual(restored.correlations, correlations)
        self.assertEqual(restored.failures, failures)
        self.assertEqual(restored.multimodal_metrics, multimodal_metrics)
        self.assertEqual(restored.auto_debug, auto_debug)
        self.assertEqual(restored.run_id, "abc123runid")

    def test_coerce_benchmark_result_accepts_instance_and_dict(self):
        result = make_benchmark_result()
        self.assertIs(coerce_benchmark_result(result), result)
        as_dict = result.to_dict()
        coerced = coerce_benchmark_result(as_dict)
        self.assertIsInstance(coerced, BenchmarkResult)
        self.assertEqual(coerced.summary.data, result.summary.data)

    def test_coerce_benchmark_result_returns_none_for_garbage(self):
        self.assertIsNone(coerce_benchmark_result(None))
        self.assertIsNone(coerce_benchmark_result("x"))
        self.assertIsNone(
            coerce_benchmark_result({"summary": {}, "rows": [{"entry_id": "bad", "question": "q"}]})
        )

    def test_coerce_accepts_foreign_benchmark_result_class(self):
        """Foreign ``BenchmarkResult`` with same name (Streamlit module reload)."""

        class BenchmarkSummary:
            def __init__(self, data: dict) -> None:
                self.data = data

            def to_dict(self) -> dict:
                return dict(self.data)

        class BenchmarkRow:
            def __init__(self, entry_id: int, question: str, data: dict) -> None:
                self.entry_id = entry_id
                self.question = question
                self.data = data

            def to_dict(self) -> dict:
                return {"entry_id": self.entry_id, "question": self.question, **self.data}

        class BenchmarkResult:
            def __init__(self, summary: BenchmarkSummary, rows: list) -> None:
                self.summary = summary
                self.rows = rows

            def to_dict(self) -> dict:
                return {
                    "summary": self.summary.to_dict(),
                    "rows": [r.to_dict() for r in self.rows],
                }

        dup = BenchmarkResult(
            BenchmarkSummary({"avg_recall_at_k": 0.5}),
            [BenchmarkRow(3, "Q?", {"confidence": 0.9})],
        )
        coerced = coerce_benchmark_result(dup)
        self.assertIsInstance(coerced, type(make_benchmark_result()))
        self.assertEqual(coerced.summary.data["avg_recall_at_k"], 0.5)
        self.assertEqual(len(coerced.rows), 1)
        self.assertEqual(coerced.rows[0].entry_id, 3)
