from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _r2(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 2)


@dataclass(frozen=True)
class EvaluationJudgeMetricsRow:
    """
    Per-row LLM-judge fields merged into :class:`~src.domain.benchmark_result.BenchmarkRow`.data.

    Built next to evaluation logic so benchmark rows stay dict-serializable for export/UI while
    the judge slice is explicit at the application boundary.
    """

    groundedness_score: float | None
    citation_faithfulness_score: float | None
    answer_relevance_score: float | None
    hallucination_score: float | None
    has_hallucination: bool | None
    answer_correctness_score: float | None
    judge_failure_reason: str | None

    def to_row_fragment(self) -> dict[str, object]:
        return {
            "groundedness_score": self.groundedness_score,
            "citation_faithfulness_score": self.citation_faithfulness_score,
            "answer_relevance_score": self.answer_relevance_score,
            "hallucination_score": self.hallucination_score,
            "has_hallucination": self.has_hallucination,
            "answer_correctness_score": self.answer_correctness_score,
            "judge_failure_reason": self.judge_failure_reason,
        }

    @staticmethod
    def from_judge_result(
        judge_result: object,
        *,
        judge_failed: bool,
        has_expected_answer: bool,
        failure_reason_fallback: str,
    ) -> EvaluationJudgeMetricsRow:
        if judge_failed:
            raw_reason = getattr(judge_result, "reason", None)
            reason = (
                raw_reason
                if isinstance(raw_reason, str) and raw_reason.strip()
                else failure_reason_fallback
            )
            return EvaluationJudgeMetricsRow(
                groundedness_score=None,
                citation_faithfulness_score=None,
                answer_relevance_score=None,
                hallucination_score=None,
                has_hallucination=None,
                answer_correctness_score=None,
                judge_failure_reason=reason,
            )

        ac_row = (
            _r2(float(getattr(judge_result, "answer_correctness_score", 0.0)))
            if has_expected_answer
            else None
        )
        return EvaluationJudgeMetricsRow(
            groundedness_score=_r2(getattr(judge_result, "groundedness_score", None)),
            citation_faithfulness_score=_r2(
                getattr(judge_result, "citation_faithfulness_score", None)
            ),
            answer_relevance_score=_r2(getattr(judge_result, "answer_relevance_score", None)),
            hallucination_score=_r2(getattr(judge_result, "hallucination_score", None)),
            has_hallucination=bool(getattr(judge_result, "has_hallucination", False)),
            answer_correctness_score=ac_row,
            judge_failure_reason=None,
        )
