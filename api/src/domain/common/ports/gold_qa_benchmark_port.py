"""Run a full gold QA benchmark (per-row pipeline + aggregate report)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

from domain.evaluation.benchmark_result import BenchmarkResult
from domain.rag.rag_inspect_answer_run import RagInspectAnswerRun


@runtime_checkable
class GoldQaBenchmarkPort(Protocol):
    def evaluate_gold_qa_dataset(
        self,
        *,
        entries: list[Any],
        pipeline_runner: Callable[[Any], RagInspectAnswerRun],
    ) -> BenchmarkResult: ...
