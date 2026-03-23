"""
Threshold-based non-regression checks for structured benchmark summaries.

Intended for CI / local validation using ``BenchmarkResult`` produced by the
evaluation layer (or synthetic fixtures). No Streamlit or LLM coupling.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.evaluation.benchmark_result import BenchmarkResult


def _summary_float(summary: dict, key: str) -> float:
    raw = summary.get(key, 0.0)
    if raw is None:
        return 0.0
    if isinstance(raw, bool):
        return float(raw)
    if isinstance(raw, (int, float)):
        return float(raw)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def _summary_int(summary: dict, key: str) -> int:
    raw = summary.get(key, 0)
    if raw is None:
        return 0
    if isinstance(raw, bool):
        return int(raw)
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float):
        return int(raw)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


@dataclass(frozen=True)
class BenchmarkRegressionThresholds:
    """
    Optional minimums on aggregate metrics from ``BenchmarkSummary.data``.

    Any field left as ``None`` is not enforced.
    """

    min_avg_recall_at_k: float | None = None
    min_avg_answer_f1: float | None = None
    min_avg_prompt_doc_id_f1: float | None = None
    min_avg_groundedness_score: float | None = None
    min_avg_answer_relevance_score: float | None = None
    min_successful_queries: int | None = None


def collect_benchmark_regression_violations(
    result: BenchmarkResult,
    thresholds: BenchmarkRegressionThresholds,
) -> list[str]:
    summary = result.summary.data
    violations: list[str] = []

    if thresholds.min_successful_queries is not None:
        actual = _summary_int(summary, "successful_queries")
        if actual < thresholds.min_successful_queries:
            violations.append(
                "successful_queries "
                f"{actual} < minimum {thresholds.min_successful_queries}"
            )

    if thresholds.min_avg_recall_at_k is not None:
        actual = _summary_float(summary, "avg_recall_at_k")
        if actual < thresholds.min_avg_recall_at_k:
            violations.append(
                "avg_recall_at_k "
                f"{actual} < minimum {thresholds.min_avg_recall_at_k}"
            )

    if thresholds.min_avg_answer_f1 is not None:
        actual = _summary_float(summary, "avg_answer_f1")
        if actual < thresholds.min_avg_answer_f1:
            violations.append(
                "avg_answer_f1 "
                f"{actual} < minimum {thresholds.min_avg_answer_f1}"
            )

    if thresholds.min_avg_prompt_doc_id_f1 is not None:
        actual = _summary_float(summary, "avg_prompt_doc_id_f1")
        if actual < thresholds.min_avg_prompt_doc_id_f1:
            violations.append(
                "avg_prompt_doc_id_f1 "
                f"{actual} < minimum {thresholds.min_avg_prompt_doc_id_f1}"
            )

    if thresholds.min_avg_groundedness_score is not None:
        actual = _summary_float(summary, "avg_groundedness_score")
        if actual < thresholds.min_avg_groundedness_score:
            violations.append(
                "avg_groundedness_score "
                f"{actual} < minimum {thresholds.min_avg_groundedness_score}"
            )

    if thresholds.min_avg_answer_relevance_score is not None:
        actual = _summary_float(summary, "avg_answer_relevance_score")
        if actual < thresholds.min_avg_answer_relevance_score:
            violations.append(
                "avg_answer_relevance_score "
                f"{actual} < minimum {thresholds.min_avg_answer_relevance_score}"
            )

    return violations


def assert_benchmark_meets_thresholds(
    result: BenchmarkResult,
    thresholds: BenchmarkRegressionThresholds,
) -> None:
    violations = collect_benchmark_regression_violations(result, thresholds)
    if violations:
        joined = "\n".join(violations)
        raise AssertionError(f"Benchmark regression thresholds violated:\n{joined}")
