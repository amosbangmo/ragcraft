"""
UI-facing types and helpers for Streamlit (API-client boundary).

Gold QA rows, benchmark results, manual evaluation, and retrieval filters use **frontend wire**
types (:mod:`services.api_contract_models`, :mod:`services.evaluation_wire_models`) so pages stay
off ``domain`` for API-shaped data. Pure presentation helpers may still live under ``domain``.
"""

from __future__ import annotations

from domain.evaluation.benchmark_comparison import (
    LOWER_IS_BETTER_METRICS,
    compare_benchmark_failure_counts,
    compare_benchmark_summaries,
)
from domain.evaluation.benchmark_failure_analysis import FailureAnalysisService
from domain.evaluation.evaluation_display_text import format_bool_toggle_on_off
from domain.rag.pipeline_payloads import PipelineBuildResult
from domain.rag.query_log_timestamp import parse_query_log_timestamp
from domain.rag.retrieval_presets import (
    PRESET_DESCRIPTIONS,
    PRESET_SELECT_ORDER,
    PRESET_UI_LABELS,
    RetrievalPreset,
    parse_retrieval_preset,
)
from domain.rag.retrieval_settings import RetrievalSettings
from services.api_contract_models import QADatasetEntryPayload, RetrievalFilters
from services.evaluation_wire_models import (
    JUDGE_FAILURE_REASON,
    BenchmarkResult,
    ManualEvaluationResult,
)
from services.evaluation_wire_parse import coerce_benchmark_result, is_manual_evaluation_result_like

# Backward-compatible alias for gold-QA entry rows (wire shape matches API / former domain row).
QADatasetEntry = QADatasetEntryPayload

__all__ = [
    "LOWER_IS_BETTER_METRICS",
    "BenchmarkResult",
    "FailureAnalysisService",
    "JUDGE_FAILURE_REASON",
    "ManualEvaluationResult",
    "PipelineBuildResult",
    "PRESET_DESCRIPTIONS",
    "PRESET_SELECT_ORDER",
    "PRESET_UI_LABELS",
    "QADatasetEntry",
    "RetrievalFilters",
    "RetrievalPreset",
    "RetrievalSettings",
    "compare_benchmark_failure_counts",
    "compare_benchmark_summaries",
    "coerce_benchmark_result",
    "format_bool_toggle_on_off",
    "is_manual_evaluation_result_like",
    "parse_query_log_timestamp",
    "parse_retrieval_preset",
]
