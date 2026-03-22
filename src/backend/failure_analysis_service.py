"""Compatibility re-export; implementation is :mod:`src.domain.benchmark_failure_analysis`."""

from __future__ import annotations

from src.domain.benchmark_failure_analysis import (
    DEFAULT_HALLUCINATION_THRESHOLD,
    DEFAULT_HIGH_CONFIDENCE_DANGEROUS,
    DEFAULT_LOW_CONFIDENCE,
    DEFAULT_QUALITY_THRESHOLD,
    DEFAULT_TOP_EXAMPLES_PER_TYPE,
    FAILURE_LABEL_ORDER,
    FailureAnalysisService,
)

__all__ = [
    "DEFAULT_HALLUCINATION_THRESHOLD",
    "DEFAULT_HIGH_CONFIDENCE_DANGEROUS",
    "DEFAULT_LOW_CONFIDENCE",
    "DEFAULT_QUALITY_THRESHOLD",
    "DEFAULT_TOP_EXAMPLES_PER_TYPE",
    "FAILURE_LABEL_ORDER",
    "FailureAnalysisService",
]
