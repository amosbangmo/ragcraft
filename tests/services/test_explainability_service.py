import unittest

from src.services.explainability_service import ExplainabilityService


class TestExplainabilityService(unittest.TestCase):
    def test_pipeline_failed_short_circuits(self) -> None:
        out = ExplainabilityService().build_explanation({"pipeline_failed": True})
        self.assertTrue(out["explanations"])
        self.assertTrue(out["suggestions"])

    def test_none_metrics_no_crash(self) -> None:
        out = ExplainabilityService().build_explanation(
            {
                "pipeline_failed": False,
                "recall_at_k": None,
                "groundedness_score": None,
                "has_hallucination": False,
            }
        )
        self.assertEqual(out["explanations"], [])
        self.assertEqual(out["suggestions"], [])

    def test_low_recall_triggers(self) -> None:
        out = ExplainabilityService().build_explanation(
            {"recall_at_k": 0.2, "has_hallucination": False}
        )
        self.assertTrue(any("recall" in e.lower() for e in out["explanations"]))

    def test_bool_not_treated_as_numeric_score(self) -> None:
        out = ExplainabilityService().build_explanation(
            {"recall_at_k": True, "has_hallucination": False}
        )
        self.assertEqual(out["explanations"], [])


if __name__ == "__main__":
    unittest.main()
