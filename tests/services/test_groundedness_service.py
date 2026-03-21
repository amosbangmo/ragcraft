import unittest
from unittest.mock import MagicMock, patch

from src.services.groundedness_service import GroundednessService


class TestGroundednessService(unittest.TestCase):
    @patch("src.services.groundedness_service.LLM")
    def test_empty_answer_returns_zero_without_llm(self, mock_llm: MagicMock) -> None:
        svc = GroundednessService()
        self.assertEqual(
            svc.compute_groundedness(question="q", answer="  ", raw_context="ctx"),
            0.0,
        )
        mock_llm.invoke.assert_not_called()

    @patch("src.services.groundedness_service.LLM")
    def test_parses_json_object_score(self, mock_llm: MagicMock) -> None:
        mock_llm.invoke.return_value = MagicMock(content='{"groundedness_score": 0.73}')
        svc = GroundednessService()
        score = svc.compute_groundedness(
            question="What is X?",
            answer="X is described in the document.",
            raw_context="The document says X is a test value.",
        )
        self.assertEqual(score, 0.73)
        mock_llm.invoke.assert_called_once()

    @patch("src.services.groundedness_service.LLM")
    def test_llm_failure_returns_zero(self, mock_llm: MagicMock) -> None:
        mock_llm.invoke.side_effect = RuntimeError("network")
        svc = GroundednessService()
        self.assertEqual(
            svc.compute_groundedness(question="q", answer="a", raw_context="c"),
            0.0,
        )

    @patch("src.services.groundedness_service.LLM")
    def test_unparseable_response_returns_zero(self, mock_llm: MagicMock) -> None:
        mock_llm.invoke.return_value = MagicMock(content="not json")
        svc = GroundednessService()
        self.assertEqual(
            svc.compute_groundedness(question="q", answer="a", raw_context="c"),
            0.0,
        )

    @patch("src.services.groundedness_service.LLM")
    def test_clamps_score_to_unit_interval(self, mock_llm: MagicMock) -> None:
        mock_llm.invoke.return_value = MagicMock(content='{"groundedness_score": 2}')
        svc = GroundednessService()
        self.assertEqual(svc.compute_groundedness(question="q", answer="a", raw_context="c"), 1.0)
