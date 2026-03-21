"""Application entry point for building benchmark JSON/CSV/Markdown export payloads."""

from __future__ import annotations

from src.application.evaluation.benchmark_export_dtos import (
    BenchmarkExportArtifacts,
    BuildBenchmarkExportCommand,
)
from src.application.evaluation.benchmark_report_formatter import BenchmarkReportFormatter


class BuildBenchmarkExportArtifactsUseCase:
    def __init__(self, *, report_formatter: BenchmarkReportFormatter | None = None) -> None:
        self._formatter = report_formatter or BenchmarkReportFormatter()

    def execute(self, command: BuildBenchmarkExportCommand) -> BenchmarkExportArtifacts:
        return self._formatter.build_artifacts(command)
