import unittest

from src.backend.auto_debug_service import AutoDebugService


class TestAutoDebugService(unittest.TestCase):
    def test_empty_summary_no_crash(self) -> None:
        out = AutoDebugService().build_suggestions({}, None)
        self.assertEqual(out, [])

    def test_none_summary_fields_ignored(self) -> None:
        out = AutoDebugService().build_suggestions(
            {
                "avg_recall_at_k": None,
                "avg_groundedness_score": None,
                "hallucination_rate": None,
            },
            None,
        )
        self.assertEqual(out, [])

    def test_low_recall_triggers(self) -> None:
        out = AutoDebugService().build_suggestions({"avg_recall_at_k": 0.2}, None)
        self.assertTrue(any("recall" in s["title"].lower() for s in out))

    def test_failure_counts_trigger(self) -> None:
        out = AutoDebugService().build_suggestions(
            {},
            {"counts": {"retrieval_failure": 2}},
        )
        self.assertTrue(any("Retrieval" in s["title"] for s in out))

    def test_judge_failure_count_triggers(self) -> None:
        out = AutoDebugService().build_suggestions(
            {},
            {"counts": {"judge_failure": 1}},
        )
        self.assertTrue(any("judge" in s["title"].lower() for s in out))

    def test_high_pipeline_failure_rate_triggers(self) -> None:
        out = AutoDebugService().build_suggestions({"pipeline_failure_rate": 0.15}, None)
        self.assertTrue(any("pipeline" in s["title"].lower() for s in out))

    def test_low_citation_doc_id_recall_triggers(self) -> None:
        out = AutoDebugService().build_suggestions({"avg_citation_doc_id_recall": 0.1}, None)
        self.assertTrue(any("citation" in s["title"].lower() for s in out))

    def test_context_selection_failure_count_triggers(self) -> None:
        out = AutoDebugService().build_suggestions(
            {},
            {"counts": {"context_selection_failure": 1}},
        )
        self.assertTrue(any("context" in s["title"].lower() for s in out))

    def test_citation_failure_count_triggers(self) -> None:
        out = AutoDebugService().build_suggestions(
            {},
            {"counts": {"citation_failure": 1}},
        )
        self.assertTrue(any("citation" in s["title"].lower() for s in out))

    def test_overconfidence_rule(self) -> None:
        out = AutoDebugService().build_suggestions(
            {"avg_confidence": 0.71, "avg_answer_f1": 0.49},
            None,
        )
        self.assertTrue(any("overconfidence" in s["title"].lower() for s in out))

    def test_overconfidence_not_triggered_when_confidence_at_threshold(self) -> None:
        out = AutoDebugService().build_suggestions(
            {"avg_confidence": 0.7, "avg_answer_f1": 0.2},
            None,
        )
        self.assertFalse(any("overconfidence" in s["title"].lower() for s in out))

    def test_failures_counts_non_dict_does_not_crash(self) -> None:
        out = AutoDebugService().build_suggestions(
            {"avg_recall_at_k": 0.9},
            {"counts": "not-a-dict"},
        )
        self.assertEqual(out, [])


if __name__ == "__main__":
    unittest.main()
