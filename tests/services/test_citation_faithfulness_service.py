import unittest
from unittest.mock import MagicMock, patch

from src.services.citation_faithfulness_service import CitationFaithfulnessService


class TestCitationFaithfulnessService(unittest.TestCase):
    @patch("src.services.citation_faithfulness_service.LLM")
    def test_empty_answer_returns_zero_without_llm(self, mock_llm: MagicMock) -> None:
        svc = CitationFaithfulnessService()
        self.assertEqual(
            svc.compute_citation_faithfulness(
                question="q",
                answer="  ",
                source_references=[{"doc_id": "d1"}],
                raw_context="ctx",
            ),
            0.0,
        )
        mock_llm.invoke.assert_not_called()

    @patch("src.services.citation_faithfulness_service.LLM")
    def test_parses_json_object_score(self, mock_llm: MagicMock) -> None:
        mock_llm.invoke.return_value = MagicMock(
            content='{"citation_faithfulness_score": 0.84, "reason": "ok"}'
        )
        svc = CitationFaithfulnessService()
        score = svc.compute_citation_faithfulness(
            question="What is X?",
            answer="According to the invoice, X is 42.",
            source_references=[{"source_file": "invoice.pdf", "doc_id": "d1"}],
            raw_context="Invoice shows X = 42.",
        )
        self.assertEqual(score, 0.84)
        mock_llm.invoke.assert_called_once()

    @patch("src.services.citation_faithfulness_service.LLM")
    def test_llm_failure_returns_zero(self, mock_llm: MagicMock) -> None:
        mock_llm.invoke.side_effect = RuntimeError("network")
        svc = CitationFaithfulnessService()
        self.assertEqual(
            svc.compute_citation_faithfulness(
                question="q",
                answer="a",
                source_references=[],
                raw_context="c",
            ),
            0.0,
        )

    @patch("src.services.citation_faithfulness_service.LLM")
    def test_unparseable_response_returns_zero(self, mock_llm: MagicMock) -> None:
        mock_llm.invoke.return_value = MagicMock(content="not json")
        svc = CitationFaithfulnessService()
        self.assertEqual(
            svc.compute_citation_faithfulness(
                question="q",
                answer="a",
                source_references=[],
                raw_context="c",
            ),
            0.0,
        )

    @patch("src.services.citation_faithfulness_service.LLM")
    def test_clamps_score_to_unit_interval(self, mock_llm: MagicMock) -> None:
        mock_llm.invoke.return_value = MagicMock(content='{"citation_faithfulness_score": 2}')
        svc = CitationFaithfulnessService()
        self.assertEqual(
            svc.compute_citation_faithfulness(
                question="q",
                answer="a",
                source_references=[],
                raw_context="c",
            ),
            1.0,
        )
