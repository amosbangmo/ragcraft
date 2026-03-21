import unittest
from unittest.mock import MagicMock, patch

from src.services.answer_relevance_service import AnswerRelevanceService


class TestAnswerRelevanceService(unittest.TestCase):
    @patch("src.services.answer_relevance_service.LLM")
    def test_empty_answer_returns_zero_without_llm(self, mock_llm):
        self.assertEqual(
            AnswerRelevanceService().compute_answer_relevance(question="q", answer="  "),
            0.0,
        )
        mock_llm.invoke.assert_not_called()

    @patch("src.services.answer_relevance_service.LLM")
    def test_parses_json_score(self, mock_llm):
        mock_llm.invoke.return_value = MagicMock(
            content='{"answer_relevance_score": 0.88, "reason": "ok"}'
        )
        svc = AnswerRelevanceService()
        score = svc.compute_answer_relevance(question="What is X?", answer="X is …")
        self.assertEqual(score, 0.88)

    @patch("src.services.answer_relevance_service.LLM")
    def test_invoke_error_returns_zero(self, mock_llm):
        mock_llm.invoke.side_effect = RuntimeError("boom")
        svc = AnswerRelevanceService()
        self.assertEqual(
            svc.compute_answer_relevance(question="q", answer="a"),
            0.0,
        )

    @patch("src.services.answer_relevance_service.LLM")
    def test_invalid_json_returns_zero(self, mock_llm):
        mock_llm.invoke.return_value = MagicMock(content="not json")
        svc = AnswerRelevanceService()
        self.assertEqual(
            svc.compute_answer_relevance(question="q", answer="a"),
            0.0,
        )

    @patch("src.services.answer_relevance_service.LLM")
    def test_clamps_score_above_one(self, mock_llm):
        mock_llm.invoke.return_value = MagicMock(content='{"answer_relevance_score": 2}')
        svc = AnswerRelevanceService()
        self.assertEqual(svc.compute_answer_relevance(question="q", answer="a"), 1.0)
