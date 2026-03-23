from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.application.use_cases.evaluation.benchmark_execution import BenchmarkExecutionUseCase
from src.domain.rag_inspect_answer_run import RagInspectAnswerRun


def test_benchmark_rejects_non_rag_inspect_answer_run() -> None:
    uc = BenchmarkExecutionUseCase(
        row_evaluation=MagicMock(),
        aggregation=MagicMock(),
        correlation=MagicMock(),
        failure_analysis=MagicMock(),
        explainability=MagicMock(),
        auto_debug=MagicMock(),
    )

    with pytest.raises(TypeError, match="RagInspectAnswerRun"):
        uc.execute(entries=[object()], pipeline_runner=lambda _e: {"not": "a run"})


def test_benchmark_accepts_rag_inspect_answer_run() -> None:
    row_eval = MagicMock()
    aggregation = MagicMock()
    aggregation.build_summary_payload.return_value = {}
    uc = BenchmarkExecutionUseCase(
        row_evaluation=row_eval,
        aggregation=aggregation,
        correlation=MagicMock(),
        failure_analysis=MagicMock(),
        explainability=MagicMock(),
        auto_debug=MagicMock(),
    )
    entry = object()
    run = RagInspectAnswerRun(pipeline=None, answer="", latency_ms=0.0, full_latency=None)

    uc.execute(entries=[entry], pipeline_runner=lambda _e: run)

    row_eval.process_row.assert_called_once()
