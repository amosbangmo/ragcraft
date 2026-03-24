"""Rule-based benchmark summary comparison (wire dicts only; mirrors domain.evaluation.benchmark_comparison)."""

from __future__ import annotations

from typing import Any

# Kept in sync with domain.evaluation.benchmark_metric_taxonomy.LOWER_IS_BETTER_METRIC_KEYS
LOWER_IS_BETTER_METRICS: frozenset[str] = frozenset(
    {
        "answer_generation_ms",
        "avg_latency_ms",
        "hallucination_flagged_rows",
        "hallucination_flagged_share",
        "hallucination_rate",
        "latency_ms",
        "pipeline_failure_rate",
        "prompt_build_ms",
        "query_rewrite_ms",
        "reranking_ms",
        "retrieval_ms",
    }
)

_CRITICAL_REGRESSION_METRICS: frozenset[str] = frozenset(
    {"avg_answer_f1", "avg_groundedness_score", "avg_answer_correctness"}
)
_CRITICAL_DELTA = -0.05


def _numeric_scalar(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def compare_benchmark_summaries(
    summary_a: dict[str, Any],
    summary_b: dict[str, Any],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    keys = sorted(set(summary_a.keys()) & set(summary_b.keys()))

    for key in keys:
        a = _numeric_scalar(summary_a.get(key))
        b = _numeric_scalar(summary_b.get(key))
        if a is None or b is None:
            continue

        delta = b - a
        lower_better = key in LOWER_IS_BETTER_METRICS

        if lower_better:
            if delta < 0:
                direction = "improved"
            elif delta > 0:
                direction = "regressed"
            else:
                direction = "neutral"
        elif delta > 0:
            direction = "improved"
        elif delta < 0:
            direction = "regressed"
            if key in _CRITICAL_REGRESSION_METRICS and delta < _CRITICAL_DELTA:
                direction = "critical_regression"
        else:
            direction = "neutral"

        results.append(
            {
                "metric": key,
                "run_a": round(a, 4),
                "run_b": round(b, 4),
                "delta": round(delta, 4),
                "direction": direction,
            }
        )

    return results


def compare_benchmark_failure_counts(
    failures_a: dict[str, Any] | None,
    failures_b: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    ca: dict[str, Any] = {}
    cb: dict[str, Any] = {}
    if isinstance(failures_a, dict):
        raw = failures_a.get("counts")
        if isinstance(raw, dict):
            ca = raw
    if isinstance(failures_b, dict):
        raw = failures_b.get("counts")
        if isinstance(raw, dict):
            cb = raw

    keys = sorted(set(ca.keys()) | set(cb.keys()))
    out: list[dict[str, Any]] = []
    for k in keys:
        va = int(ca.get(k, 0) or 0)
        vb = int(cb.get(k, 0) or 0)
        out.append(
            {
                "failure_type": str(k),
                "run_a": va,
                "run_b": vb,
                "delta": vb - va,
            }
        )
    out.sort(key=lambda r: (-abs(int(r["delta"])), str(r["failure_type"]).lower()))
    return out
