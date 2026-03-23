import unittest

from components.shared.evaluation_summary_metrics import coerce_float_for_summary_metric


class TestCoerceFloatForSummaryMetric(unittest.TestCase):
    def test_none_and_invalid(self) -> None:
        self.assertIsNone(coerce_float_for_summary_metric(None))
        self.assertIsNone(coerce_float_for_summary_metric("x"))
        self.assertIsNone(coerce_float_for_summary_metric(True))

    def test_numeric(self) -> None:
        self.assertEqual(coerce_float_for_summary_metric(3), 3.0)
        self.assertEqual(coerce_float_for_summary_metric("2.5"), 2.5)


if __name__ == "__main__":
    unittest.main()
