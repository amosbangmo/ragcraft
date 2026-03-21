import unittest

import pandas as pd

from src.ui import evaluation_dashboard as ed


class TestEvaluationDashboardCoercions(unittest.TestCase):
    def test_coerce_float(self) -> None:
        self.assertIsNone(ed._coerce_float(None))
        self.assertIsNone(ed._coerce_float("x"))
        self.assertIsNone(ed._coerce_float(True))
        self.assertEqual(ed._coerce_float(3), 3.0)
        self.assertEqual(ed._coerce_float("2.5"), 2.5)

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


if __name__ == "__main__":
    unittest.main()
