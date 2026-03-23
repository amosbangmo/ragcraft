"""Application-layer benchmark export (no heavy ingestion imports)."""

from __future__ import annotations

from application.dto.benchmark_export import BuildBenchmarkExportCommand
from application.orchestration.evaluation.build_benchmark_export_artifacts import (
    BuildBenchmarkExportArtifactsUseCase,
)
from domain.evaluation.benchmark_result import BenchmarkResult, BenchmarkSummary


def test_build_benchmark_export_produces_three_artifacts() -> None:
    result = BenchmarkResult(summary=BenchmarkSummary(data={"rows": 0}), rows=[])
    uc = BuildBenchmarkExportArtifactsUseCase()
    out = uc.execute(
        BuildBenchmarkExportCommand(
            project_id="demo",
            result=result,
            enable_query_rewrite=False,
            enable_hybrid_retrieval=True,
        )
    )
    assert out.json_bytes
    assert out.csv_bytes
    assert out.markdown_bytes
    assert out.json_filename.endswith(".json")
    assert ".csv" in out.csv_filename
    assert out.markdown_filename.endswith(".md")
