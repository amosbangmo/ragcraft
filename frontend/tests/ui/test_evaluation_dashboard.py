import unittest

import pandas as pd

from components.shared import evaluation_dashboard as ed
from domain.evaluation.benchmark_comparison import LOWER_IS_BETTER_METRICS
from infrastructure.evaluation.benchmark_comparison_service import BenchmarkComparisonService


class TestEvaluationDashboardCoercions(unittest.TestCase):
    def test_coerce_float_alias_matches_shared_helper(self) -> None:
        from components.shared.evaluation_summary_metrics import coerce_float_for_summary_metric

        self.assertIs(ed._coerce_float, coerce_float_for_summary_metric)

    def test_coerce_hallucination_flag(self) -> None:
        self.assertTrue(ed._coerce_hallucination_flag(True))
        self.assertFalse(ed._coerce_hallucination_flag(False))
        self.assertTrue(ed._coerce_hallucination_flag("yes"))
        self.assertTrue(ed._coerce_hallucination_flag(1))
        self.assertFalse(ed._coerce_hallucination_flag(0))
        self.assertFalse(ed._coerce_hallucination_flag("maybe"))

    def test_row_hallucination_flag(self) -> None:
        self.assertTrue(ed._row_hallucination_flag({"has_hallucination": True}))
        self.assertFalse(ed._row_hallucination_flag({"has_hallucination": False}))
        self.assertFalse(
            ed._row_hallucination_flag({"judge_failed": True, "has_hallucination": True})
        )
        self.assertFalse(ed._row_hallucination_flag({"judge_failed": True}))
        self.assertFalse(ed._row_hallucination_flag({}))

    def test_row_answer_text_priority(self) -> None:
        self.assertEqual(
            ed._row_answer_text(
                {"answer": " full ", "answer_preview": "prev", "generated_answer": "gen"}
            ),
            "full",
        )
        self.assertEqual(
            ed._row_answer_text({"answer_preview": "preview only"}),
            "preview only",
        )
        self.assertEqual(
            ed._row_answer_text({"generated_answer": "generated"}),
            "generated",
        )
        self.assertIsNone(ed._row_answer_text({}))


class TestEvaluationDashboardNumericSeries(unittest.TestCase):
    def test_numeric_series_first_column_with_data(self) -> None:
        df = pd.DataFrame({"a": ["x"], "b": [1.0]})
        s = ed._numeric_series(df, "a", "b")
        self.assertIsNotNone(s)
        assert s is not None
        self.assertAlmostEqual(float(s.iloc[0]), 1.0)

    def test_numeric_series_none_when_missing(self) -> None:
        df = pd.DataFrame({"a": ["nope"]})
        self.assertIsNone(ed._numeric_series(df, "missing"))


class TestDataframeJudgeValidForHallucination(unittest.TestCase):
    def test_excludes_judge_failed_rows(self) -> None:
        df = pd.DataFrame(
            [
                {"judge_failed": True, "has_hallucination": True},
                {"judge_failed": False, "has_hallucination": True},
            ]
        )
        out = ed._dataframe_judge_valid_for_hallucination(df)
        self.assertEqual(len(out), 1)
        self.assertFalse(bool(out.iloc[0]["judge_failed"]))

    def test_passthrough_when_no_judge_failed_column(self) -> None:
        df = pd.DataFrame([{"has_hallucination": True}])
        out = ed._dataframe_judge_valid_for_hallucination(df)
        self.assertEqual(len(out), 1)


class TestComparisonLowerIsBetterAlignment(unittest.TestCase):
    def test_dashboard_uses_service_lower_is_better_set(self) -> None:
        self.assertIs(ed.LOWER_IS_BETTER_METRICS, LOWER_IS_BETTER_METRICS)

    def test_improved_metrics_split_by_direction_semantics(self) -> None:
        a = {"avg_latency_ms": 100.0, "avg_recall_at_k": 0.5, "hallucination_rate": 0.2}
        b = {"avg_latency_ms": 90.0, "avg_recall_at_k": 0.6, "hallucination_rate": 0.1}
        rows = BenchmarkComparisonService().compare(a, b)
        df = pd.DataFrame(rows)
        improved = df[df["direction"] == "improved"]
        lo = improved[improved["metric"].isin(LOWER_IS_BETTER_METRICS)]
        hi = improved[~improved["metric"].isin(LOWER_IS_BETTER_METRICS)]
        self.assertEqual(set(lo["metric"]), {"avg_latency_ms", "hallucination_rate"})
        self.assertEqual(set(hi["metric"]), {"avg_recall_at_k"})


class TestEvaluationDashboardResolveFailurePayload(unittest.TestCase):
    def test_uses_nonempty_failures_dict(self) -> None:
        payload = {"counts": {"retrieval_failure": 2}, "failed_row_count": 2}
        out = ed._resolve_failure_payload(payload, rows=[])
        self.assertEqual(out, payload)

    def test_empty_failures_recomputes_from_rows(self) -> None:
        rows = [
            {
                "entry_id": 1,
                "question": "q",
                "recall_at_k": 0.0,
                "expected_doc_ids_count": 1,
            }
        ]
        out = ed._resolve_failure_payload({}, rows=rows)
        self.assertIsInstance(out, dict)
        self.assertNotIn("row_failures", out)
        self.assertIn("counts", out)

    def test_none_failures_with_empty_rows(self) -> None:
        self.assertIsNone(ed._resolve_failure_payload(None, rows=[]))

    def test_empty_failures_dict_recomputes_from_rows(self) -> None:
        rows = [
            {
                "entry_id": 1,
                "question": "q",
                "recall_at_k": 0.0,
                "expected_doc_ids_count": 1,
            }
        ]
        out = ed._resolve_failure_payload({}, rows=rows)
        self.assertIsInstance(out, dict)
        self.assertIn("counts", out)


if __name__ == "__main__":
    unittest.main()
