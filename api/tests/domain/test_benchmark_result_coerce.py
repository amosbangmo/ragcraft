from __future__ import annotations

from domain.evaluation.benchmark_result import (
    BenchmarkResult,
    BenchmarkRow,
    BenchmarkSummary,
    coerce_benchmark_result,
)


def test_to_dict_round_trip() -> None:
    r = BenchmarkResult(
        summary=BenchmarkSummary(data={"rows": 1}),
        rows=[BenchmarkRow(1, "q", {"answer_f1": 0.5})],
        correlations={"x": 1},
        failures={"counts": {"a": 1}},
        multimodal_metrics={"table_usage_rate": 0.1},
        auto_debug=[{"title": "t", "description": "d"}],
        run_id="rid",
    )
    d = r.to_dict()
    r2 = BenchmarkResult.from_plain_dict(d)
    assert r2.run_id == "rid"
    assert len(r2.rows) == 1
    assert r2.auto_debug == [{"title": "t", "description": "d"}]


def test_from_plain_dict_auto_debug_filters_non_str() -> None:
    r = BenchmarkResult.from_plain_dict(
        {
            "summary": {},
            "rows": [],
            "auto_debug": [{"title": 1, "description": "d"}, {"title": "ok", "description": "x"}],
        }
    )
    assert r.auto_debug == [{"title": "ok", "description": "x"}]


def test_coerce_benchmark_result_instance() -> None:
    r = BenchmarkResult(summary=BenchmarkSummary(), rows=[])
    assert coerce_benchmark_result(r) is r


def test_coerce_benchmark_result_dict() -> None:
    r = coerce_benchmark_result({"summary": {}, "rows": []})
    assert isinstance(r, BenchmarkResult)


def test_coerce_benchmark_result_invalid() -> None:
    assert coerce_benchmark_result(None) is None
    assert coerce_benchmark_result("x") is None


def test_from_plain_dict_row_skips_invalid() -> None:
    r = BenchmarkResult.from_plain_dict(
        {
            "summary": {},
            "rows": [{}, {"entry_id": "1", "question": "q"}],
        }
    )
    assert len(r.rows) == 1
    assert r.rows[0].entry_id == 1
