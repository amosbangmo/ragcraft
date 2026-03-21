import unittest
from unittest.mock import patch

from src.services.reranking_service import RerankingService


class TestRerankingService(unittest.TestCase):
    def test_table_boost_reorders_when_scores_close(self) -> None:
        svc = RerankingService()
        assets = [
            {"doc_id": "t1", "content_type": "text", "raw_content": "alpha beta", "metadata": {}},
            {"doc_id": "tb1", "content_type": "table", "raw_content": "<table></table>", "metadata": {}},
        ]
        with patch.object(svc, "_score_candidates", return_value=[1.0, 0.85]):
            out = svc.rerank(
                "query",
                assets,
                2,
                prefer_tables=True,
                table_boost=0.2,
            )
        self.assertEqual(out[0].get("content_type"), "table")
        self.assertEqual(out[0].get("doc_id"), "tb1")

    def test_without_prefer_tables_no_boost(self) -> None:
        svc = RerankingService()
        assets = [
            {"doc_id": "t1", "content_type": "text", "raw_content": "alpha beta", "metadata": {}},
            {"doc_id": "tb1", "content_type": "table", "raw_content": "<table></table>", "metadata": {}},
        ]
        with patch.object(svc, "_score_candidates", return_value=[1.0, 0.85]):
            out = svc.rerank("query", assets, 2, prefer_tables=False, table_boost=0.5)
        self.assertEqual(out[0].get("content_type"), "text")


if __name__ == "__main__":
    unittest.main()
