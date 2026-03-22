"""Bridges :class:`~src.domain.ports.gold_qa_benchmark_port.GoldQaBenchmarkPort` to benchmark execution (composition-owned)."""

from __future__ import annotations

from typing import Any

from src.application.use_cases.evaluation.benchmark_execution import BenchmarkExecutionUseCase
from src.domain.benchmark_result import BenchmarkResult


class GoldQaBenchmarkAdapter:
    """
    Implements gold-QA dataset evaluation by delegating to :class:`BenchmarkExecutionUseCase`.

    Wired in :mod:`src.composition.evaluation_wiring` so infrastructure never imports application use cases.
    """

    def __init__(self, benchmark_execution: BenchmarkExecutionUseCase) -> None:
        self._benchmark_execution = benchmark_execution

    def evaluate_gold_qa_dataset(
        self,
        *,
        entries: list[Any],
        pipeline_runner,
    ) -> BenchmarkResult:
        return self._benchmark_execution.execute(
            entries=entries,
            pipeline_runner=pipeline_runner,
        )
