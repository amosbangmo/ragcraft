import unittest

from src.domain.evaluation_display_text import (
    BENCHMARK_MARKDOWN_NOTE_JUDGE_AGGREGATES,
    format_bool_toggle_on_off,
)


class TestFormatBoolToggleOnOff(unittest.TestCase):
    def test_values(self) -> None:
        self.assertEqual(format_bool_toggle_on_off(True), "on")
        self.assertEqual(format_bool_toggle_on_off(False), "off")


class TestBenchmarkMarkdownNotes(unittest.TestCase):
    def test_judge_aggregate_note_mentions_judge_failed(self) -> None:
        self.assertIn("judge_failed", BENCHMARK_MARKDOWN_NOTE_JUDGE_AGGREGATES)


if __name__ == "__main__":
    unittest.main()
