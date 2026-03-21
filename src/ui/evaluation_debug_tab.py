"""
Debug tab: advanced benchmark dashboard, JSON, and raw manual assets.
"""

from __future__ import annotations

from typing import Any

from src.domain.benchmark_result import BenchmarkResult
from src.domain.manual_evaluation_result import ManualEvaluationResult
from src.ui.evaluation_debug import render_evaluation_debug


def render_evaluation_debug_tab(debug_payload: dict[str, Any]) -> None:
    bench = debug_payload.get("benchmark_result")
    manual = debug_payload.get("manual_result")
    render_evaluation_debug(
        benchmark_result=bench if isinstance(bench, BenchmarkResult) else None,
        manual_result=manual if isinstance(manual, ManualEvaluationResult) else None,
    )
