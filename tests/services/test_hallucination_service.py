import unittest
from unittest.mock import MagicMock, patch

from src.services.hallucination_service import HallucinationService


class TestHallucinationService(unittest.TestCase):
    @patch("src.services.hallucination_service.LLM")
    def test_empty_answer_returns_supported_without_llm(self, mock_llm: MagicMock) -> None:
        self.assertEqual(
            HallucinationService().compute_hallucination(
                question="q",
                answer="  ",
                raw_context="ctx",
            ),
            (1.0, False),
        )
        mock_llm.invoke.assert_not_called()

    @patch("src.services.hallucination_service.LLM")
    def test_no_hallucination_case(self, mock_llm: MagicMock) -> None:
        mock_llm.invoke.return_value = MagicMock(
            content='{"hallucination_score": 1.0, "has_hallucination": false}'
        )
        svc = HallucinationService()
        score, flag = svc.compute_hallucination(
            question="What is X?",
            answer="X is described in the context.",
            raw_context="The document says X is blue.",
        )
        self.assertEqual(score, 1.0)
        self.assertFalse(flag)

    @patch("src.services.hallucination_service.LLM")
    def test_partial_hallucination_case(self, mock_llm: MagicMock) -> None:
        mock_llm.invoke.return_value = MagicMock(
            content='{"hallucination_score": 0.6, "has_hallucination": true, "reason": "Extra claim."}'
        )
        svc = HallucinationService()
        score, flag = svc.compute_hallucination(
            question="q",
            answer="a",
            raw_context="c",
        )
        self.assertEqual(score, 0.6)
        self.assertTrue(flag)

    @patch("src.services.hallucination_service.LLM")
    def test_full_hallucination_case(self, mock_llm: MagicMock) -> None:
        mock_llm.invoke.return_value = MagicMock(
            content='{"hallucination_score": 0.0, "has_hallucination": true}'
        )
        svc = HallucinationService()
        score, flag = svc.compute_hallucination(
            question="q",
            answer="a",
            raw_context="c",
        )
        self.assertEqual(score, 0.0)
        self.assertTrue(flag)

    @patch("src.services.hallucination_service.LLM")
    def test_invoke_error_returns_conservative_fallback(self, mock_llm: MagicMock) -> None:
        mock_llm.invoke.side_effect = RuntimeError("unavailable")
        svc = HallucinationService()
        self.assertEqual(
            svc.compute_hallucination(question="q", answer="a", raw_context="c"),
            (0.0, True),
        )

    @patch("src.services.hallucination_service.LLM")
    def test_invalid_json_returns_fallback(self, mock_llm: MagicMock) -> None:
        mock_llm.invoke.return_value = MagicMock(content="not json")
        svc = HallucinationService()
        self.assertEqual(
            svc.compute_hallucination(question="q", answer="a", raw_context="c"),
            (0.0, True),
        )

    @patch("src.services.hallucination_service.LLM")
    def test_clamps_score_above_one(self, mock_llm: MagicMock) -> None:
        mock_llm.invoke.return_value = MagicMock(
            content='{"hallucination_score": 2, "has_hallucination": false}'
        )
        svc = HallucinationService()
        score, flag = svc.compute_hallucination(question="q", answer="a", raw_context="c")
        self.assertEqual(score, 1.0)
        self.assertFalse(flag)

    @patch("src.services.hallucination_service.LLM")
    def test_infers_has_hallucination_when_omitted(self, mock_llm: MagicMock) -> None:
        mock_llm.invoke.return_value = MagicMock(content='{"hallucination_score": 0.95}')
        svc = HallucinationService()
        score, flag = svc.compute_hallucination(question="q", answer="a", raw_context="c")
        self.assertEqual(score, 0.95)
        self.assertTrue(flag)
