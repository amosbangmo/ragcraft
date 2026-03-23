import unittest

from infrastructure.evaluation.explainability_service import ExplainabilityService


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

    def test_judge_failed_skips_judge_metrics_but_keeps_retrieval(self) -> None:
        out = ExplainabilityService().build_explanation(
            {
                "judge_failed": True,
                "judge_failure_reason": "judge_failure",
                "recall_at_k": 0.2,
                "has_hallucination": True,
                "groundedness_score": 0.0,
                "answer_relevance_score": 0.0,
            }
        )
        expl = " ".join(out["explanations"]).lower()
        self.assertIn("judge", expl)
        self.assertTrue(any("recall" in e.lower() for e in out["explanations"]))
        self.assertFalse(any("hallucinat" in e.lower() for e in out["explanations"]))

    def test_judge_failed_custom_reason_appended(self) -> None:
        out = ExplainabilityService().build_explanation(
            {"judge_failed": True, "judge_failure_reason": "provider timeout"}
        )
        self.assertTrue(any("timeout" in e.lower() for e in out["explanations"]))


if __name__ == "__main__":
    unittest.main()
