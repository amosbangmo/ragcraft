import unittest
from unittest.mock import patch

from src.domain.query_intent import QueryIntent
from src.backend.query_intent_service import QueryIntentService


class TestQueryIntentService(unittest.TestCase):
    def setUp(self) -> None:
        self.svc = QueryIntentService()

    def test_empty_and_none_fallback_unknown(self) -> None:
        self.assertEqual(self.svc.classify(None), QueryIntent.UNKNOWN)
        self.assertEqual(self.svc.classify(""), QueryIntent.UNKNOWN)
        self.assertEqual(self.svc.classify("   "), QueryIntent.UNKNOWN)

    def test_comparison_keywords(self) -> None:
        self.assertEqual(
            self.svc.classify("Compare product A vs product B"),
            QueryIntent.COMPARISON,
        )
        self.assertEqual(
            self.svc.classify("What is the difference between X and Y?"),
            QueryIntent.COMPARISON,
        )

    def test_table_keywords(self) -> None:
        self.assertEqual(self.svc.classify("Show values in the third row"), QueryIntent.TABLE)
        self.assertEqual(self.svc.classify("Which column has revenue?"), QueryIntent.TABLE)
        self.assertEqual(
            self.svc.classify("What are the metrics reported in the final table?"),
            QueryIntent.TABLE,
        )
        self.assertEqual(
            self.svc.classify("Which quarter had the highest revenue?"),
            QueryIntent.TABLE,
        )
        self.assertEqual(
            self.svc.classify("What does the table show about latency?"),
            QueryIntent.TABLE,
        )

    def test_compare_values_phrase_is_table_before_generic_comparison(self) -> None:
        self.assertEqual(
            self.svc.classify("Compare the values in Table 2."),
            QueryIntent.TABLE,
        )

    def test_image_keywords(self) -> None:
        self.assertEqual(self.svc.classify("What does figure 3 show?"), QueryIntent.IMAGE)
        self.assertEqual(self.svc.classify("Describe the chart on page 2"), QueryIntent.IMAGE)

    def test_exploratory_length_and_phrases(self) -> None:
        self.assertEqual(self.svc.classify("Give me an overview of the attached documents"), QueryIntent.EXPLORATORY)
        long_q = " ".join(["word"] * 30)
        self.assertEqual(self.svc.classify(long_q), QueryIntent.EXPLORATORY)

    def test_factual_short_questions(self) -> None:
        self.assertEqual(self.svc.classify("What is the capital of France?"), QueryIntent.FACTUAL)
        self.assertEqual(self.svc.classify("Who signed the contract?"), QueryIntent.FACTUAL)

    def test_unknown_when_no_signal(self) -> None:
        self.assertEqual(
            self.svc.classify(
                "one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen"
            ),
            QueryIntent.UNKNOWN,
        )

    def test_classify_never_raises(self) -> None:
        with patch(
            "src.domain.retrieval.query_intent_classification._classify_query_intent_inner",
            side_effect=RuntimeError("boom"),
        ):
            self.assertEqual(QueryIntentService().classify("hello"), QueryIntent.UNKNOWN)


if __name__ == "__main__":
    unittest.main()
