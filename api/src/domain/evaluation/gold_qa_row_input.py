"""Typed input for gold-QA row evaluation (replaces ad hoc dict passed to row processors)."""

from __future__ import annotations

from dataclasses import dataclass

from domain.rag.pipeline_latency import PipelineLatency
from domain.rag.pipeline_payloads import PipelineBuildResult


@dataclass(frozen=True)
class GoldQaPipelineRowInput:
    """One inspect+answer outcome for :class:`~infrastructure.evaluation.row_evaluation_service.RowEvaluationService`."""

    pipeline: PipelineBuildResult | None
    answer: str
    latency_ms: float
    full_latency: PipelineLatency | None
