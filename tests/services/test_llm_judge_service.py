import unittest
from unittest.mock import MagicMock, patch

from src.domain.llm_judge_result import LLMJudgeResult
from src.services.llm_judge_service import LLMJudgeService


class TestLLMJudgeService(unittest.TestCase):
    def test_empty_answer_skips_llm(self) -> None:
        with patch.object(LLMJudgeService, "_failure_result") as mock_fail:
            r = LLMJudgeService().evaluate(
                question="q",
                answer="   ",
                raw_context="ctx",
                prompt_sources=[],
            )
        mock_fail.assert_not_called()
        self.assertEqual(
            r,
            LLMJudgeResult(
                groundedness_score=0.0,
                answer_relevance_score=0.0,
                hallucination_score=1.0,
                has_hallucination=False,
                reason=None,
            ),
        )

    @patch("src.services.llm_judge_service.LLM")
    def test_parse_full_json(self, mock_llm: MagicMock) -> None:
        mock_llm.invoke.return_value = MagicMock(
            content=(
                '{"groundedness_score": 0.9, '
                '"answer_relevance_score": 0.88, "hallucination_score": 0.92, '
                '"has_hallucination": false, "reason": "ok"}'
            )
        )
        r = LLMJudgeService().evaluate(
            question="q?",
            answer="The answer.",
            raw_context="some context",
            prompt_sources=[{"doc_id": "d1"}],
        )
        self.assertEqual(r.groundedness_score, 0.9)
        self.assertEqual(r.answer_relevance_score, 0.88)
        self.assertEqual(r.hallucination_score, 0.92)
        self.assertFalse(r.has_hallucination)
        self.assertEqual(r.reason, "ok")

    @patch("src.services.llm_judge_service.LLM")
    def test_extra_legacy_keys_in_json_are_ignored(self, mock_llm: MagicMock) -> None:
        mock_llm.invoke.return_value = MagicMock(
            content=(
                '{"groundedness_score": 0.8, "prompt_source_alignment_score": 0.77, '
                '"answer_relevance_score": 0.7, "hallucination_score": 0.9, '
                '"has_hallucination": false}'
            )
        )
        r = LLMJudgeService().evaluate(
            question="q",
            answer="a",
            raw_context="c",
            prompt_sources=[],
        )
        self.assertEqual(r.groundedness_score, 0.8)
        self.assertEqual(r.answer_relevance_score, 0.7)

    @patch("src.services.llm_judge_service.LLM")
    def test_strips_markdown_fence(self, mock_llm: MagicMock) -> None:
        mock_llm.invoke.return_value = MagicMock(
            content="```json\n"
            '{"groundedness_score": 1, '
            '"answer_relevance_score": 1, "hallucination_score": 1, '
            '"has_hallucination": false}\n'
            "```"
        )
        r = LLMJudgeService().evaluate(
            question="q",
            answer="a",
            raw_context="c",
            prompt_sources=[],
        )
        self.assertEqual(r.groundedness_score, 1.0)
        self.assertFalse(r.has_hallucination)

    @patch("src.services.llm_judge_service.LLM")
    def test_llm_invoke_exception_returns_failure_defaults(self, mock_llm: MagicMock) -> None:
        mock_llm.invoke.side_effect = RuntimeError("unavailable")
        r = LLMJudgeService().evaluate(
            question="q",
            answer="a",
            raw_context="c",
            prompt_sources=[],
        )
        self.assertEqual(r, LLMJudgeService._failure_result())

    @patch("src.services.llm_judge_service.LLM")
    def test_unparseable_response_returns_failure_defaults(self, mock_llm: MagicMock) -> None:
        mock_llm.invoke.return_value = MagicMock(content="not json at all")
        r = LLMJudgeService().evaluate(
            question="q",
            answer="a",
            raw_context="c",
            prompt_sources=[],
        )
        self.assertEqual(r, LLMJudgeService._failure_result())

    @patch("src.services.llm_judge_service.LLM")
    def test_regex_fallback_when_json_invalid(self, mock_llm: MagicMock) -> None:
        mock_llm.invoke.return_value = MagicMock(
            content='noise {"groundedness_score": 0.7, "garbage" trailing '
            '"answer_relevance_score": 0.72 '
            '"hallucination_score": 0.73, "has_hallucination": true}'
        )
        r = LLMJudgeService().evaluate(
            question="q",
            answer="a",
            raw_context="c",
            prompt_sources=[],
        )
        self.assertEqual(r.groundedness_score, 0.7)
        self.assertEqual(r.answer_relevance_score, 0.72)
        self.assertEqual(r.hallucination_score, 0.73)
        self.assertTrue(r.has_hallucination)


if __name__ == "__main__":
    unittest.main()
