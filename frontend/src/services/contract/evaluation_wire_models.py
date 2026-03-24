"""
Evaluation JSON wire shapes for the Streamlit HTTP client (no ``domain.evaluation`` imports).

Aligned with FastAPI response bodies; use :mod:`services.contract.evaluation_wire_parse` to build instances
from plain dicts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

JUDGE_FAILURE_REASON = "judge_failure"


@dataclass(frozen=True)
class ManualEvaluationAnswerQuality:
    confidence: float
    groundedness_score: float | None
    citation_faithfulness_score: float | None
    answer_relevance_score: float | None
    hallucination_score: float | None
    has_hallucination: bool | None
    answer_f1: float | None = None
    answer_correctness_score: float | None = None
    semantic_similarity: float | None = None

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
    ndcg_at_k: float | None = None

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
    pipeline_failed: bool = False
    judge_failed: bool = False
    judge_failure_reason: str | None = None
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
            "pipeline_failed": self.pipeline_failed,
            "judge_failed": self.judge_failed,
            "judge_failure_reason": self.judge_failure_reason,
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


@dataclass(frozen=True)
class BenchmarkRunMetadata:
    project_id: str
    generated_at_utc: str
    enable_query_rewrite: bool
    enable_hybrid_retrieval: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "generated_at_utc": self.generated_at_utc,
            "enable_query_rewrite": self.enable_query_rewrite,
            "enable_hybrid_retrieval": self.enable_hybrid_retrieval,
        }


@dataclass(frozen=True)
class BenchmarkRow:
    entry_id: int
    question: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "question": self.question,
            **dict(self.data),
        }


@dataclass(frozen=True)
class BenchmarkSummary:
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.data)


@dataclass(frozen=True)
class BenchmarkResult:
    summary: BenchmarkSummary
    rows: list[BenchmarkRow] = field(default_factory=list)
    correlations: dict[str, Any] | None = None
    failures: dict[str, Any] | None = None
    multimodal_metrics: dict[str, Any] | None = None
    auto_debug: list[dict[str, str]] | None = None
    run_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "summary": self.summary.to_dict(),
            "rows": [row.to_dict() for row in self.rows],
        }
        if self.correlations is not None:
            out["correlations"] = dict(self.correlations)
        if self.failures is not None:
            out["failures"] = dict(self.failures)
        if self.multimodal_metrics is not None:
            out["multimodal_metrics"] = dict(self.multimodal_metrics)
        if self.auto_debug is not None:
            out["auto_debug"] = [dict(item) for item in self.auto_debug]
        if self.run_id is not None:
            out["run_id"] = self.run_id
        return out

    @classmethod
    def from_plain_dict(cls, payload: dict[str, Any]) -> BenchmarkResult:
        summary_raw = payload.get("summary")
        if not isinstance(summary_raw, dict):
            summary_raw = {}
        rows_raw = payload.get("rows")
        if not isinstance(rows_raw, list):
            rows_raw = []
        summary = BenchmarkSummary(data=dict(summary_raw))
        rows: list[BenchmarkRow] = []
        reserved = frozenset({"entry_id", "question"})
        for item in rows_raw:
            if not isinstance(item, dict) or "entry_id" not in item:
                continue
            entry_id = int(item["entry_id"])
            q = item.get("question", "")
            question = q if isinstance(q, str) else str(q)
            data = {k: v for k, v in item.items() if k not in reserved}
            rows.append(BenchmarkRow(entry_id=entry_id, question=question, data=data))
        corr_raw = payload.get("correlations")
        correlations: dict[str, Any] | None = None
        if isinstance(corr_raw, dict):
            correlations = dict(corr_raw)
        fail_raw = payload.get("failures")
        failures: dict[str, Any] | None = None
        if isinstance(fail_raw, dict):
            failures = dict(fail_raw)
        mm_raw = payload.get("multimodal_metrics")
        multimodal_metrics: dict[str, Any] | None = None
        if isinstance(mm_raw, dict):
            multimodal_metrics = dict(mm_raw)
        ad_raw = payload.get("auto_debug")
        auto_debug: list[dict[str, str]] | None = None
        if isinstance(ad_raw, list):
            parsed: list[dict[str, str]] = []
            for item in ad_raw:
                if not isinstance(item, dict):
                    continue
                t = item.get("title")
                d = item.get("description")
                if isinstance(t, str) and isinstance(d, str):
                    parsed.append({"title": t, "description": d})
            auto_debug = parsed
        rid_raw = payload.get("run_id")
        run_id: str | None = rid_raw if isinstance(rid_raw, str) and rid_raw.strip() else None
        return cls(
            summary=summary,
            rows=rows,
            correlations=correlations,
            failures=failures,
            multimodal_metrics=multimodal_metrics,
            auto_debug=auto_debug,
            run_id=run_id,
        )
