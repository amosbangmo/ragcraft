"""Parse evaluation API JSON into :mod:`services.evaluation_wire_models` instances."""

from __future__ import annotations

from dataclasses import fields
from typing import Any

from services.evaluation_wire_models import (
    BenchmarkResult,
    ManualEvaluationAnswerCitationQuality,
    ManualEvaluationAnswerQuality,
    ManualEvaluationExpectationComparison,
    ManualEvaluationPipelineSignals,
    ManualEvaluationPromptSourceQuality,
    ManualEvaluationResult,
    ManualEvaluationRetrievalQuality,
)


def _optional_subdataclass(cls: type, raw: Any) -> Any:
    if raw is None or not isinstance(raw, dict):
        return None
    try:
        kwargs: dict[str, Any] = {}
        for f in fields(cls):
            kwargs[f.name] = raw.get(f.name)
        return cls(**kwargs)
    except TypeError:
        return None


def _pipeline_signals_from_plain_dict(raw: Any) -> ManualEvaluationPipelineSignals | None:
    if raw is None or not isinstance(raw, dict):
        return None
    sl = raw.get("stage_latency")
    stage_latency: dict[str, float] | None = None
    if isinstance(sl, dict):
        stage_latency = {str(k): float(v) for k, v in sl.items() if isinstance(v, (int, float))}
    try:
        return ManualEvaluationPipelineSignals(
            confidence=float(raw.get("confidence") or 0.0),
            retrieval_mode=str(raw.get("retrieval_mode") or ""),
            query_rewrite_enabled=bool(raw.get("query_rewrite_enabled")),
            hybrid_retrieval_enabled=bool(raw.get("hybrid_retrieval_enabled")),
            latency_ms=float(raw.get("latency_ms") or 0.0),
            stage_latency=stage_latency,
        )
    except TypeError:
        return None


def manual_evaluation_result_from_plain_dict(d: dict[str, Any]) -> ManualEvaluationResult:
    return ManualEvaluationResult(
        question=str(d.get("question") or ""),
        answer=str(d.get("answer") or ""),
        expected_answer=d.get("expected_answer"),
        confidence=float(d.get("confidence") or 0.0),
        pipeline_failed=bool(d.get("pipeline_failed")),
        judge_failed=bool(d.get("judge_failed")),
        judge_failure_reason=d.get("judge_failure_reason"),
        prompt_sources=list(d.get("prompt_sources") or []),
        raw_assets=list(d.get("raw_assets") or []),
        answer_quality=_optional_subdataclass(ManualEvaluationAnswerQuality, d.get("answer_quality")),
        answer_citation_quality=_optional_subdataclass(
            ManualEvaluationAnswerCitationQuality, d.get("answer_citation_quality")
        ),
        prompt_source_quality=_optional_subdataclass(
            ManualEvaluationPromptSourceQuality, d.get("prompt_source_quality")
        ),
        retrieval_quality=_optional_subdataclass(
            ManualEvaluationRetrievalQuality, d.get("retrieval_quality")
        ),
        pipeline_signals=_pipeline_signals_from_plain_dict(d.get("pipeline_signals")),
        expectation_comparison=_optional_subdataclass(
            ManualEvaluationExpectationComparison, d.get("expectation_comparison")
        ),
        detected_issues=list(d.get("detected_issues") or []),
    )


def coerce_benchmark_result(value: Any) -> BenchmarkResult | None:
    if isinstance(value, BenchmarkResult):
        return value
    if isinstance(value, dict):
        try:
            return BenchmarkResult.from_plain_dict(value)
        except (TypeError, ValueError, KeyError):
            return None
    to_dict = getattr(value, "to_dict", None)
    if type(value).__name__ == "BenchmarkResult" and callable(to_dict):
        try:
            dumped = to_dict()
            if isinstance(dumped, dict):
                return BenchmarkResult.from_plain_dict(dumped)
        except (TypeError, ValueError, KeyError):
            return None
    return None


def is_manual_evaluation_result_like(value: Any) -> bool:
    return isinstance(value, ManualEvaluationResult) or (
        type(value).__name__ == "ManualEvaluationResult"
        and hasattr(value, "question")
        and hasattr(value, "answer")
    )
