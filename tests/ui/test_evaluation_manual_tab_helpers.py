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


if __name__ == "__main__":
    unittest.main()
