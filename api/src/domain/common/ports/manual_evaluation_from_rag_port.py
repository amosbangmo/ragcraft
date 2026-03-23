"""Assemble a manual evaluation result after RAG inspect + answer."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from domain.evaluation.manual_evaluation_result import ManualEvaluationResult
from domain.rag.pipeline_latency import PipelineLatency
from domain.rag.pipeline_payloads import PipelineBuildResult


@runtime_checkable
class ManualEvaluationFromRagPort(Protocol):
    def build_manual_evaluation_result(
        self,
        *,
        user_id: str,
        project_id: str,
        question: str,
        expected_answer: str | None,
        expected_doc_ids: list[str],
        expected_sources: list[str],
        pipeline: PipelineBuildResult | None,
        answer: str,
        latency_ms: float,
        full_latency: PipelineLatency | None,
    ) -> ManualEvaluationResult: ...
