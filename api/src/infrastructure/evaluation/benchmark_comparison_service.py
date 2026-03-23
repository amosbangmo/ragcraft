from __future__ import annotations

from typing import Any

from domain.evaluation.benchmark_comparison import (
    LOWER_IS_BETTER_METRICS,
    compare_benchmark_failure_counts,
    compare_benchmark_summaries,
)


class BenchmarkComparisonService:
    """
    Compare two benchmark summary dicts (run A vs B) and compute metric deltas.
    Rule-based only; no LLM calls.
    """

    def compare(
        self,
        summary_a: dict[str, Any],
        summary_b: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return compare_benchmark_summaries(summary_a, summary_b)

    def compare_failure_counts(
        self,
        failures_a: dict[str, Any] | None,
        failures_b: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        return compare_benchmark_failure_counts(failures_a, failures_b)
