"""Narrow ports for :class:`~application.use_cases.evaluation.benchmark_execution.BenchmarkExecutionUseCase`."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from domain.evaluation.benchmark_accumulator import BenchmarkAccumulator
from domain.evaluation.gold_qa_row_input import GoldQaPipelineRowInput


@runtime_checkable
class BenchmarkRowProcessingPort(Protocol):
    def process_row(
        self, entry: Any, result: GoldQaPipelineRowInput, acc: BenchmarkAccumulator
    ) -> None: ...


@runtime_checkable
class BenchmarkSummaryAggregationPort(Protocol):
    def build_summary_payload(self, acc: BenchmarkAccumulator) -> dict: ...


@runtime_checkable
class CorrelationComputePort(Protocol):
    def compute(self, rows: list[dict[str, Any]]) -> dict[str, Any]: ...


@runtime_checkable
class BenchmarkFailureAnalysisPort(Protocol):
    def analyze(self, row_dicts: list[dict[str, Any]]) -> dict[str, Any]: ...


@runtime_checkable
class ExplainabilityBuildPort(Protocol):
    def build_explanation(self, row: dict[str, Any]) -> dict[str, Any]: ...


@runtime_checkable
class AutoDebugSuggestionsPort(Protocol):
    def build_suggestions(
        self,
        summary_payload: dict[str, Any],
        failures_report: dict[str, Any],
    ) -> dict[str, Any]: ...
