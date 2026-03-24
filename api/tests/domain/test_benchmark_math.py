from __future__ import annotations

from domain.evaluation.benchmark_math import latency_stage_row_fields, mean_round, r2, rate
from domain.rag.pipeline_latency import PipelineLatency


def test_latency_stage_row_fields_with_none() -> None:
    d = latency_stage_row_fields(None)
    assert "query_rewrite_ms" in d


def test_r2_none() -> None:
    assert r2(None) is None


def test_mean_round_empty() -> None:
    assert mean_round([], 2) is None


def test_mean_round_values() -> None:
    assert mean_round([1.0, 2.0], 2) == 1.5


def test_rate_zero_denominator() -> None:
    assert rate(1, 0) is None


def test_rate_ok() -> None:
    assert rate(1, 4) == 0.25
