"""
Gold-QA benchmark stack: application :class:`~src.application.use_cases.evaluation.benchmark_execution.BenchmarkExecutionUseCase`
plus infrastructure row/metric services.

**Layering:** this module may import both ``src.application.use_cases`` and ``src.infrastructure.adapters``;
infrastructure adapters must not import application use cases (see architecture tests).

Wiring is linear: no optional dependency branching. Tests override pieces via
:class:`EvaluationWiringParts` + :func:`dataclasses.replace`.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.application.use_cases.evaluation.benchmark_execution import BenchmarkExecutionUseCase
from src.application.use_cases.evaluation.gold_qa_benchmark_adapter import GoldQaBenchmarkAdapter
from src.domain.benchmark_failure_analysis import FailureAnalysisService
from src.infrastructure.adapters.evaluation.answer_quality_aggregation_service import (
    AnswerQualityAggregationService,
)
from src.infrastructure.adapters.evaluation.auto_debug_service import AutoDebugService
from src.infrastructure.adapters.evaluation.benchmark_aggregation_service import BenchmarkAggregationService
from src.infrastructure.adapters.evaluation.correlation_service import CorrelationService
from src.infrastructure.adapters.evaluation.evaluation_service import EvaluationService
from src.infrastructure.adapters.evaluation.explainability_service import ExplainabilityService
from src.infrastructure.adapters.evaluation.llm_judge_service import LLMJudgeService
from src.infrastructure.adapters.evaluation.retrieval_metrics_service import RetrievalMetricsService
from src.infrastructure.adapters.evaluation.row_evaluation_service import RowEvaluationService
from src.infrastructure.adapters.evaluation.semantic_similarity_service import SemanticSimilarityService


@dataclass(frozen=True)
class EvaluationWiringParts:
    """Concrete collaborators for :func:`build_evaluation_service` (composition-only bundle)."""

    llm_judge_service: object
    correlation_service: CorrelationService
    failure_analysis_service: FailureAnalysisService
    semantic_similarity_service: object
    explainability_service: ExplainabilityService
    auto_debug_service: AutoDebugService


def default_evaluation_wiring_parts() -> EvaluationWiringParts:
    """Process-default evaluation adapters (no conditionals; used by :func:`build_backend_composition`)."""
    return EvaluationWiringParts(
        llm_judge_service=LLMJudgeService(),
        correlation_service=CorrelationService(),
        failure_analysis_service=FailureAnalysisService(),
        semantic_similarity_service=SemanticSimilarityService(),
        explainability_service=ExplainabilityService(),
        auto_debug_service=AutoDebugService(),
    )


def build_evaluation_service(parts: EvaluationWiringParts) -> EvaluationService:
    """
    Construct :class:`~src.infrastructure.adapters.evaluation.evaluation_service.EvaluationService`
    with a fully wired :class:`~src.domain.ports.gold_qa_benchmark_port.GoldQaBenchmarkPort` implementation.
    """
    retrieval_metrics = RetrievalMetricsService()
    answer_quality = AnswerQualityAggregationService()
    row_evaluation = RowEvaluationService(
        retrieval_metrics_service=retrieval_metrics,
        answer_quality_service=answer_quality,
        semantic_similarity_service=parts.semantic_similarity_service,
        llm_judge_service=parts.llm_judge_service,
    )
    benchmark_execution = BenchmarkExecutionUseCase(
        row_evaluation=row_evaluation,
        aggregation=BenchmarkAggregationService(),
        correlation=parts.correlation_service,
        failure_analysis=parts.failure_analysis_service,
        explainability=parts.explainability_service,
        auto_debug=parts.auto_debug_service,
    )
    gold_qa = GoldQaBenchmarkAdapter(benchmark_execution)

    return EvaluationService(
        gold_qa_benchmark=gold_qa,
        retrieval_metrics_service=retrieval_metrics,
        answer_quality_service=answer_quality,
    )


__all__ = [
    "EvaluationWiringParts",
    "build_evaluation_service",
    "default_evaluation_wiring_parts",
]
