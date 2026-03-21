from dataclasses import dataclass


@dataclass
class LLMJudgeResult:
    groundedness_score: float
    answer_relevance_score: float
    hallucination_score: float
    has_hallucination: bool
    reason: str | None = None

    def to_dict(self) -> dict:
        return {
            "groundedness_score": self.groundedness_score,
            "answer_relevance_score": self.answer_relevance_score,
            "hallucination_score": self.hallucination_score,
            "has_hallucination": self.has_hallucination,
            "reason": self.reason,
        }
