"""Payload for evaluation flows that run inspect-pipeline then answer generation (no query logging)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.domain.pipeline_latency import PipelineLatency
from src.domain.pipeline_payloads import PipelineBuildResult


@dataclass(frozen=True)
class RagInspectAnswerRun:
    """Result of one RAG turn used for manual or gold-QA evaluation (inspect + answer + latency)."""

    pipeline: PipelineBuildResult | None
    answer: str
    latency_ms: float
    full_latency: PipelineLatency | None

    def to_row_evaluation_dict(self) -> dict[str, Any]:
        """Shape expected by :meth:`RowEvaluationService.process_row`."""
        return {
            "pipeline": self.pipeline,
            "answer": self.answer,
            "latency_ms": self.latency_ms,
            "latency": self.full_latency.to_dict() if self.full_latency is not None else None,
        }
