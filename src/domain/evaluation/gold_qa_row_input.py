"""Typed input for gold-QA row evaluation (replaces ad hoc dict passed to row processors)."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.pipeline_latency import PipelineLatency
from src.domain.pipeline_payloads import PipelineBuildResult


@dataclass(frozen=True)
class GoldQaPipelineRowInput:
    """One inspect+answer outcome for :class:`~src.infrastructure.adapters.evaluation.row_evaluation_service.RowEvaluationService`."""

    pipeline: PipelineBuildResult | None
    answer: str
    latency_ms: float
    full_latency: PipelineLatency | None
