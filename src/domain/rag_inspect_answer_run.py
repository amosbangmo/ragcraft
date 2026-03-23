"""Payload for evaluation flows that run inspect-pipeline then answer generation (no query logging)."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.evaluation.gold_qa_row_input import GoldQaPipelineRowInput
from src.domain.pipeline_latency import PipelineLatency
from src.domain.pipeline_payloads import PipelineBuildResult


@dataclass(frozen=True)
class RagInspectAnswerRun:
    """Result of one RAG turn used for manual or gold-QA evaluation (inspect + answer + latency)."""

    pipeline: PipelineBuildResult | None
    answer: str
    latency_ms: float
    full_latency: PipelineLatency | None

    def as_row_evaluation_input(self) -> GoldQaPipelineRowInput:
        """Typed input for :meth:`~src.infrastructure.adapters.evaluation.row_evaluation_service.RowEvaluationService.process_row`."""
        return GoldQaPipelineRowInput(
            pipeline=self.pipeline,
            answer=self.answer,
            latency_ms=self.latency_ms,
            full_latency=self.full_latency,
        )
