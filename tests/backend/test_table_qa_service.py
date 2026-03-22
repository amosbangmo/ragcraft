import unittest

from src.domain.query_intent import QueryIntent
from src.backend.table_qa_service import TableQAService


class TestTableQAService(unittest.TestCase):
    def setUp(self) -> None:
        self.svc = TableQAService()

    def test_table_intent_always_table_query(self) -> None:
        self.assertTrue(
            self.svc.is_table_query(
                query_intent=QueryIntent.TABLE,
                question="anything",
            )
        )

    def test_comparison_with_table_reference(self) -> None:
        self.assertTrue(
            self.svc.is_table_query(
                query_intent=QueryIntent.COMPARISON,
                question="Compare the figures in table 2",
            )
        )

    def test_comparison_without_table_not_table_query(self) -> None:
        self.assertFalse(
            self.svc.is_table_query(
                query_intent=QueryIntent.COMPARISON,
                question="Compare product A vs product B",
            )
        )


if __name__ == "__main__":
    unittest.main()
