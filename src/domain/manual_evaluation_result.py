from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class ManualEvaluationAnswerQuality:
    confidence: float
    groundedness_score: float | None
    citation_faithfulness_score: float | None
    answer_relevance_score: float | None
    hallucination_score: float | None
    has_hallucination: bool | None
    answer_f1: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ManualEvaluationAnswerCitationQuality:
    citation_doc_id_precision: float | None
    citation_doc_id_recall: float | None
    citation_doc_id_f1: float | None
    citation_doc_id_overlap_count: int | None
    citation_doc_ids_count: int | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ManualEvaluationPromptSourceQuality:
    prompt_doc_id_precision: float | None
    prompt_doc_id_recall: float | None
    prompt_doc_id_f1: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ManualEvaluationRetrievalQuality:
    recall_at_k: float | None
    source_recall: float | None
    precision_at_k: float | None
    reciprocal_rank: float | None
    average_precision: float | None
    retrieved_doc_ids_count: int
    selected_source_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ManualEvaluationPipelineSignals:
    confidence: float
    retrieval_mode: str
    query_rewrite_enabled: bool
    hybrid_retrieval_enabled: bool
    latency_ms: float
    stage_latency: dict[str, float] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ManualEvaluationExpectationComparison:
    expected_doc_ids: list[str]
    retrieved_doc_ids: list[str]
    matched_doc_ids: list[str]
    missing_doc_ids: list[str]
    expected_sources: list[str]
    retrieved_sources: list[str]
    matched_sources: list[str]
    missing_sources: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ManualEvaluationResult:
    question: str
    answer: str
    expected_answer: str | None
    confidence: float
    prompt_sources: list[dict[str, Any]] = field(default_factory=list)
    raw_assets: list[dict[str, Any]] = field(default_factory=list)
    answer_quality: ManualEvaluationAnswerQuality | None = None
    answer_citation_quality: ManualEvaluationAnswerCitationQuality | None = None
    prompt_source_quality: ManualEvaluationPromptSourceQuality | None = None
    retrieval_quality: ManualEvaluationRetrievalQuality | None = None
    pipeline_signals: ManualEvaluationPipelineSignals | None = None
    expectation_comparison: ManualEvaluationExpectationComparison | None = None
    detected_issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "answer": self.answer,
            "expected_answer": self.expected_answer,
            "confidence": self.confidence,
            "prompt_sources": list(self.prompt_sources),
            "raw_assets": list(self.raw_assets),
            "answer_quality": self.answer_quality.to_dict() if self.answer_quality else None,
            "answer_citation_quality": self.answer_citation_quality.to_dict()
            if self.answer_citation_quality
            else None,
            "prompt_source_quality": self.prompt_source_quality.to_dict()
            if self.prompt_source_quality
            else None,
            "retrieval_quality": self.retrieval_quality.to_dict() if self.retrieval_quality else None,
            "pipeline_signals": self.pipeline_signals.to_dict() if self.pipeline_signals else None,
            "expectation_comparison": self.expectation_comparison.to_dict()
            if self.expectation_comparison
            else None,
            "detected_issues": list(self.detected_issues),
        }


def is_manual_evaluation_result_like(value: Any) -> bool:
    """
    True for ManualEvaluationResult instances.

    After Streamlit reruns, ``isinstance(x, ManualEvaluationResult)`` can fail while
    ``type(x).__name__`` is still ``ManualEvaluationResult`` (duplicate class object).
    """
    if value is None or isinstance(value, dict):
        return False
    if isinstance(value, ManualEvaluationResult):
        return True
    return (
        type(value).__name__ == "ManualEvaluationResult"
        and hasattr(value, "answer")
        and hasattr(value, "question")
        and hasattr(value, "confidence")
    )
