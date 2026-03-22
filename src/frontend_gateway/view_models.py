"""
UI-facing types and helpers for Streamlit (API-client boundary).

Re-exports domain contracts so ``pages/`` and ``src/ui`` avoid importing ``src.domain`` directly,
matching how a separate SPA would consume shared wire/view types.
"""

from __future__ import annotations

from src.domain.benchmark_comparison import (
    LOWER_IS_BETTER_METRICS,
    compare_benchmark_failure_counts,
    compare_benchmark_summaries,
)
from src.domain.benchmark_failure_analysis import FailureAnalysisService
from src.domain.benchmark_result import BenchmarkResult, coerce_benchmark_result
from src.domain.evaluation_display_text import format_bool_toggle_on_off
from src.domain.llm_judge_constants import JUDGE_FAILURE_REASON
from src.domain.manual_evaluation_result import ManualEvaluationResult, is_manual_evaluation_result_like
from src.domain.pipeline_payloads import PipelineBuildResult
from src.domain.qa_dataset_entry import QADatasetEntry
from src.domain.query_log_timestamp import parse_query_log_timestamp
from src.domain.retrieval_filters import RetrievalFilters
from src.domain.retrieval_presets import (
    PRESET_DESCRIPTIONS,
    PRESET_SELECT_ORDER,
    PRESET_UI_LABELS,
    RetrievalPreset,
    parse_retrieval_preset,
)
from src.domain.retrieval_settings import RetrievalSettings

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
