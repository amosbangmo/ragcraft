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

    def test_structured_table_headers_in_candidate_text(self) -> None:
        svc = RerankingService()
        asset = {
            "doc_id": "t1",
            "content_type": "table",
            "raw_content": "<table></table>",
            "metadata": {
                "structured_table": {"headers": ["Revenue", "Year"], "rows": []},
            },
        }
        text = svc._build_candidate_text(asset)
        self.assertIn("Revenue", text)
        self.assertIn("Year", text)

    def test_image_candidate_text_includes_summary_and_surrounding(self) -> None:
        svc = RerankingService()
        asset = {
            "doc_id": "i1",
            "content_type": "image",
            "raw_content": "base64blob",
            "summary": "Bar chart of sales by region.",
            "metadata": {
                "image_title": "Regional sales",
                "surrounding_text": "Figure 4 compares Q1 and Q2.",
            },
        }
        text = svc._build_candidate_text(asset)
        self.assertIn("Regional sales", text)
        self.assertIn("Q1", text)
        self.assertIn("Bar chart", text)

    def test_rerank_empty_inputs(self) -> None:
        svc = RerankingService()
        self.assertEqual(svc.rerank("", [{"doc_id": "d"}], 3), [])
        self.assertEqual(svc.rerank("q", [], 3), [])
        self.assertEqual(svc.rerank("q", [{"doc_id": "d"}], 0), [])

    def test_fallback_score_and_tokenize(self) -> None:
        svc = RerankingService()
        self.assertEqual(svc._fallback_score("", "hello world"), 0.0)
        score = svc._fallback_score("alpha beta", "alpha beta gamma")
        self.assertGreater(score, 0.4)

    @patch.object(RerankingService, "_get_model")
    def test_score_candidates_uses_cross_encoder(self, mock_get_model) -> None:
        mock_model = mock_get_model.return_value
        mock_model.predict.return_value = [0.1, 0.9]
        svc = RerankingService()
        candidates = [
            {"candidate_text": "a"},
            {"candidate_text": "b"},
        ]
        scores = svc._score_candidates("q", candidates)
        self.assertEqual(scores, [0.1, 0.9])

    @patch.object(RerankingService, "_get_model")
    def test_score_candidates_falls_back_on_predict_error(self, mock_get_model) -> None:
        mock_model = mock_get_model.return_value
        mock_model.predict.side_effect = RuntimeError("fail")
        svc = RerankingService()
        candidates = [{"candidate_text": "hello world"}]
        scores = svc._score_candidates("hello", candidates)
        self.assertEqual(len(scores), 1)
        self.assertGreaterEqual(scores[0], 0.0)


if __name__ == "__main__":
    unittest.main()
