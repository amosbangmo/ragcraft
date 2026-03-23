"""
UI-facing types and helpers for Streamlit (API-client boundary).

Re-exports domain contracts so ``frontend/src/pages`` and ``frontend/src/components`` avoid
importing ``domain`` directly, matching how a separate SPA would consume shared wire/view types.
"""

from __future__ import annotations

from domain.evaluation.benchmark_comparison import (
    LOWER_IS_BETTER_METRICS,
    compare_benchmark_failure_counts,
    compare_benchmark_summaries,
)
from domain.evaluation.benchmark_failure_analysis import FailureAnalysisService
from domain.evaluation.benchmark_result import BenchmarkResult, coerce_benchmark_result
from domain.evaluation.evaluation_display_text import format_bool_toggle_on_off
from domain.evaluation.llm_judge_constants import JUDGE_FAILURE_REASON
from domain.evaluation.manual_evaluation_result import (
    ManualEvaluationResult,
    is_manual_evaluation_result_like,
)
from domain.evaluation.qa_dataset_entry import QADatasetEntry
from domain.rag.pipeline_payloads import PipelineBuildResult
from domain.rag.query_log_timestamp import parse_query_log_timestamp
from domain.rag.retrieval_filters import RetrievalFilters
from domain.rag.retrieval_presets import (
    PRESET_DESCRIPTIONS,
    PRESET_SELECT_ORDER,
    PRESET_UI_LABELS,
    RetrievalPreset,
    parse_retrieval_preset,
)
from domain.rag.retrieval_settings import RetrievalSettings

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
