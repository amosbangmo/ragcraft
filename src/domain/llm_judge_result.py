from dataclasses import dataclass


@dataclass
class LLMJudgeResult:
    groundedness_score: float
    citation_faithfulness_score: float
    answer_relevance_score: float
    hallucination_score: float
    has_hallucination: bool
    answer_correctness_score: float = 0.0
    reason: str | None = None

    def to_dict(self) -> dict:
        return {
            "groundedness_score": self.groundedness_score,
            "citation_faithfulness_score": self.citation_faithfulness_score,
            "answer_relevance_score": self.answer_relevance_score,
            "hallucination_score": self.hallucination_score,
            "has_hallucination": self.has_hallucination,
            "answer_correctness_score": self.answer_correctness_score,
            "reason": self.reason,
        }
