from __future__ import annotations

from types import SimpleNamespace

from domain.evaluation.judge_metrics_row import EvaluationJudgeMetricsRow


def test_to_row_fragment() -> None:
    r = EvaluationJudgeMetricsRow(
        groundedness_score=0.5,
        citation_faithfulness_score=None,
        answer_relevance_score=0.3,
        hallucination_score=0.2,
        has_hallucination=False,
        answer_correctness_score=0.9,
        judge_failure_reason=None,
    )
    d = r.to_row_fragment()
    assert d["groundedness_score"] == 0.5


def test_from_judge_result_when_failed_uses_reason() -> None:
    jr = SimpleNamespace(reason="custom")
    r = EvaluationJudgeMetricsRow.from_judge_result(
        jr, judge_failed=True, has_expected_answer=True, failure_reason_fallback="fb"
    )
    assert r.judge_failure_reason == "custom"
    assert r.groundedness_score is None


def test_from_judge_result_when_failed_empty_reason_fallback() -> None:
    jr = SimpleNamespace(reason="  ")
    r = EvaluationJudgeMetricsRow.from_judge_result(
        jr, judge_failed=True, has_expected_answer=True, failure_reason_fallback="fb"
    )
    assert r.judge_failure_reason == "fb"


def test_from_judge_success_with_expected_answer() -> None:
    jr = SimpleNamespace(
        groundedness_score=0.8,
        citation_faithfulness_score=0.7,
        answer_relevance_score=0.6,
        hallucination_score=0.1,
        has_hallucination=True,
        answer_correctness_score=0.95,
    )
    r = EvaluationJudgeMetricsRow.from_judge_result(
        jr, judge_failed=False, has_expected_answer=True, failure_reason_fallback="x"
    )
    assert r.answer_correctness_score == 0.95
    assert r.has_hallucination is True


def test_from_judge_success_without_expected_answer() -> None:
    jr = SimpleNamespace(
        groundedness_score=0.5,
        citation_faithfulness_score=None,
        answer_relevance_score=None,
        hallucination_score=None,
        has_hallucination=False,
        answer_correctness_score=0.9,
    )
    r = EvaluationJudgeMetricsRow.from_judge_result(
        jr, judge_failed=False, has_expected_answer=False, failure_reason_fallback="x"
    )
    assert r.answer_correctness_score is None
