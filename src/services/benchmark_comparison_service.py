from __future__ import annotations

from typing import Any

_CRITICAL_REGRESSION_METRICS = frozenset({"avg_answer_f1", "avg_groundedness_score"})
_CRITICAL_DELTA = -0.05


def _numeric_scalar(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


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
        results: list[dict[str, Any]] = []
        keys = sorted(set(summary_a.keys()) & set(summary_b.keys()))

        for key in keys:
            a = _numeric_scalar(summary_a.get(key))
            b = _numeric_scalar(summary_b.get(key))
            if a is None or b is None:
                continue

            delta = b - a

            if delta > 0:
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

    def compare_failure_counts(
        self,
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
        return out
