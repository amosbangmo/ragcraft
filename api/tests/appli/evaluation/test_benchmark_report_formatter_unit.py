from __future__ import annotations

from datetime import UTC, datetime

from application.dto.benchmark_export import BuildBenchmarkExportCommand
from application.evaluation.benchmark_report_formatter import (
    BenchmarkReportFormatter,
    coerce_generated_at,
    iso_utc,
    safe_filename_segment,
    utc_timestamp_for_filename,
)
from domain.evaluation.benchmark_result import BenchmarkResult, BenchmarkRow, BenchmarkSummary


def test_utc_timestamp_for_filename_naive() -> None:
    s = utc_timestamp_for_filename(datetime(2024, 1, 2, 3, 4, 5))
    assert s.startswith("20240102")


def test_iso_utc_offset() -> None:
    s = iso_utc(datetime(2024, 1, 1, 12, 0, tzinfo=UTC))
    assert s.endswith("Z")


def test_coerce_generated_at_variants() -> None:
    assert coerce_generated_at(None) is None
    assert coerce_generated_at("") is None
    assert coerce_generated_at("not-a-date") is None
    assert coerce_generated_at(datetime.now(UTC)) is not None
    assert coerce_generated_at("2024-01-01T00:00:00Z") is not None


def test_safe_filename_segment() -> None:
    assert "project" in safe_filename_segment("   ")
    assert safe_filename_segment("ab")[:2] == "ab"


def test_build_artifacts_full_markdown_branches() -> None:
    result = BenchmarkResult(
        summary=BenchmarkSummary(data={"avg_x": 1}),
        rows=[
            BenchmarkRow(1, "q1|pipe", {"answer_f1": 0.5, "long": "x" * 200}),
        ],
        failures={
            "counts": {"retrieval_failure": 2},
            "failed_row_count": 2,
            "critical_count": 1,
        },
        auto_debug=[
            {"title": "t", "description": "d"},
            {"title": "", "description": ""},
            {"title": "only", "description": ""},
        ],
        correlations={"pearson": 0.5},
        multimodal_metrics={"table_usage_rate": 0.2},
        run_id="run-1",
    )
    cmd = BuildBenchmarkExportCommand(
        project_id="demo/proj",
        result=result,
        enable_query_rewrite=True,
        enable_hybrid_retrieval=False,
        generated_at=datetime(2025, 6, 1, 12, 0, 0, tzinfo=UTC),
    )
    art = BenchmarkReportFormatter().build_artifacts(cmd)
    assert art.json_bytes
    assert b"entry_id" in art.csv_bytes
    assert b"RAGCraft benchmark" in art.markdown_bytes
    assert "ragcraft_benchmark" in art.json_filename


def test_build_artifacts_empty_rows() -> None:
    result = BenchmarkResult(summary=BenchmarkSummary(data={}), rows=[])
    cmd = BuildBenchmarkExportCommand(
        project_id="p",
        result=result,
        enable_query_rewrite=False,
        enable_hybrid_retrieval=False,
    )
    art = BenchmarkReportFormatter().build_artifacts(cmd)
    assert b"No benchmark rows" in art.markdown_bytes
