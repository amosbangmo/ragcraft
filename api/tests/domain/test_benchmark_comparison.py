from __future__ import annotations

from domain.evaluation.benchmark_comparison import (
    compare_benchmark_failure_counts,
    compare_benchmark_summaries,
)


def test_compare_summaries_lower_better_improved() -> None:
    out = compare_benchmark_summaries({"latency_ms": 10.0}, {"latency_ms": 8.0})
    assert any(r["metric"] == "latency_ms" and r["direction"] == "improved" for r in out)


def test_compare_summaries_higher_better_regressed() -> None:
    out = compare_benchmark_summaries({"custom_up": 0.9}, {"custom_up": 0.7})
    assert any(r["metric"] == "custom_up" and r["direction"] == "regressed" for r in out)


def test_compare_summaries_critical_regression() -> None:
    out = compare_benchmark_summaries({"avg_answer_f1": 1.0}, {"avg_answer_f1": 0.89})
    crit = [r for r in out if r["metric"] == "avg_answer_f1"]
    assert crit and crit[0]["direction"] == "critical_regression"


def test_compare_summaries_skips_bool_and_missing() -> None:
    out = compare_benchmark_summaries({"x": True, "y": 1}, {"x": False, "y": 2})
    assert not any(r["metric"] == "x" for r in out)


def test_compare_summaries_neutral_equal() -> None:
    out = compare_benchmark_summaries({"m": 1.0}, {"m": 1.0})
    assert any(r["direction"] == "neutral" for r in out)


def test_compare_summaries_lower_better_neutral() -> None:
    out = compare_benchmark_summaries({"latency_ms": 5.0}, {"latency_ms": 5.0})
    assert any(r["metric"] == "latency_ms" and r["direction"] == "neutral" for r in out)


def test_compare_failure_counts_sorting() -> None:
    out = compare_benchmark_failure_counts(
        {"counts": {"a": 2, "b": 1}},
        {"counts": {"a": 0, "b": 5}},
    )
    assert out[0]["failure_type"] == "b"
