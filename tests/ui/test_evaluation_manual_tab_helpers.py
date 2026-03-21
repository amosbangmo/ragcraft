import unittest

from src.ui.evaluation_csv_utils import parse_evaluation_csv_list


class TestParseEvaluationCsvList(unittest.TestCase):
    def test_empty(self) -> None:
        self.assertEqual(parse_evaluation_csv_list(""), [])
        self.assertEqual(parse_evaluation_csv_list("   "), [])

    def test_splits_trims_dedupes(self) -> None:
        self.assertEqual(
            parse_evaluation_csv_list(" a, b , a , c"),
            ["a", "b", "c"],
        )

    def test_unicode_tokens(self) -> None:
        self.assertEqual(parse_evaluation_csv_list("café, naïve"), ["café", "naïve"])

    def test_skips_empty_segments(self) -> None:
        self.assertEqual(parse_evaluation_csv_list("a,,,b"), ["a", "b"])


if __name__ == "__main__":
    unittest.main()
