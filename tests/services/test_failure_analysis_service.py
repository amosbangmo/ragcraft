import unittest

from src.services.failure_analysis_service import FailureAnalysisService


class TestFailureAnalysisService(unittest.TestCase):
    def test_empty_rows(self) -> None:
        out = FailureAnalysisService().analyze([])
        self.assertEqual(out["failed_row_count"], 0)
        self.assertEqual(out["row_failures"], [])
        self.assertEqual(out["counts"], {})

    def test_hallucination_uses_low_score_as_risk(self) -> None:
        """Judge scores: high hallucination_score means better (less hallucination)."""
        rows = [
            {
                "entry_id": 1,
                "question": "Q?",
                "has_expected_answer": False,
                "expected_doc_ids_count": 0,
                "hallucination_score": 0.2,
                "has_hallucination": False,
            }
        ]
        out = FailureAnalysisService().analyze(rows)
        self.assertIn("hallucination", out["row_failures"][0]["failure_labels"])

    def test_has_hallucination_flag_overrides_high_score(self) -> None:
        rows = [
            {
                "entry_id": 2,
                "question": "Q?",
                "has_expected_answer": False,
                "expected_doc_ids_count": 0,
                "hallucination_score": 0.95,
                "has_hallucination": True,
            }
        ]
        out = FailureAnalysisService().analyze(rows)
        self.assertIn("hallucination", out["row_failures"][0]["failure_labels"])

    def test_critical_high_confidence_low_gold_f1(self) -> None:
        rows = [
            {
                "entry_id": 3,
                "question": "Q?",
                "has_expected_answer": True,
                "answer_f1": 0.1,
                "confidence": 0.9,
                "expected_doc_ids_count": 0,
            }
        ]
        out = FailureAnalysisService().analyze(rows)
        self.assertTrue(out["row_failures"][0]["failure_critical"])
        self.assertGreater(out["critical_count"], 0)

    def test_missing_metrics_skipped_without_crash(self) -> None:
        rows = [{"entry_id": 4, "question": "Bare"}]
        out = FailureAnalysisService().analyze(rows)
        self.assertEqual(out["failed_row_count"], 0)
        self.assertEqual(out["row_failures"][0]["failure_labels"], [])

    def test_retrieval_mode_none(self) -> None:
        rows = [
            {
                "entry_id": 5,
                "question": "Q?",
                "retrieval_mode": "none",
                "expected_doc_ids_count": 0,
            }
        ]
        out = FailureAnalysisService().analyze(rows)
        self.assertIn("retrieval_failure", out["row_failures"][0]["failure_labels"])

    def test_table_misuse_when_table_context_and_low_gold_f1(self) -> None:
        rows = [
            {
                "entry_id": 6,
                "question": "Q?",
                "has_expected_answer": True,
                "answer_f1": 0.1,
                "context_uses_table": True,
                "expected_doc_ids_count": 0,
            }
        ]
        out = FailureAnalysisService().analyze(rows)
        self.assertIn("table_misuse", out["row_failures"][0]["failure_labels"])

    def test_image_hallucination_when_image_context_and_hallucination(self) -> None:
        rows = [
            {
                "entry_id": 7,
                "question": "Q?",
                "has_expected_answer": False,
                "context_uses_image": True,
                "hallucination_score": 0.1,
                "has_hallucination": False,
                "expected_doc_ids_count": 0,
            }
        ]
        out = FailureAnalysisService().analyze(rows)
        self.assertIn("image_hallucination", out["row_failures"][0]["failure_labels"])


if __name__ == "__main__":
    unittest.main()
