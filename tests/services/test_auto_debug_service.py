import unittest

from src.services.auto_debug_service import AutoDebugService


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


if __name__ == "__main__":
    unittest.main()
