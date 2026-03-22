"""
Service façade for benchmark exports.

Formatting lives in :mod:`src.application.evaluation.benchmark_report_formatter`;
orchestration entry point is
:class:`~src.application.evaluation.use_cases.build_benchmark_export_artifacts.BuildBenchmarkExportArtifactsUseCase`.
"""

from __future__ import annotations

from src.application.evaluation.benchmark_export_dtos import (
    BenchmarkExportArtifacts,
    BuildBenchmarkExportCommand,
)
from src.application.evaluation.benchmark_report_formatter import (
    coerce_generated_at,
    safe_filename_segment,
)
from src.application.evaluation.use_cases.build_benchmark_export_artifacts import (
    BuildBenchmarkExportArtifactsUseCase,
)


class BenchmarkReportService:
    """Thin adapter for callers that still inject a report service (tests, legacy wiring)."""

    def __init__(self) -> None:
        self._use_case = BuildBenchmarkExportArtifactsUseCase()

    def build_export_artifacts(
        self,
        *,
        project_id: str,
        result,
        enable_query_rewrite: bool,
        enable_hybrid_retrieval: bool,
        generated_at=None,
    ) -> BenchmarkExportArtifacts:
        return self._use_case.execute(
            BuildBenchmarkExportCommand(
                project_id=project_id,
                result=result,
                enable_query_rewrite=enable_query_rewrite,
                enable_hybrid_retrieval=enable_hybrid_retrieval,
                generated_at=generated_at,
            )
        )


__all__ = [
    "BenchmarkExportArtifacts",
    "BenchmarkReportService",
    "BuildBenchmarkExportCommand",
    "coerce_generated_at",
    "safe_filename_segment",
]
