"""
Gold-QA benchmark stack: application :class:`~src.application.use_cases.evaluation.benchmark_execution.BenchmarkExecutionUseCase`
plus infrastructure row/metric services.

**Layering:** this module may import both ``src.application.use_cases`` and ``src.infrastructure.adapters``;
infrastructure adapters must not import application use cases (see architecture tests).
"""

from __future__ import annotations

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


def build_evaluation_service(
    *,
    llm_judge_service: object | None = None,
    correlation_service: CorrelationService | None = None,
    failure_analysis_service: FailureAnalysisService | None = None,
    semantic_similarity_service: object | None = None,
    explainability_service: ExplainabilityService | None = None,
    auto_debug_service: AutoDebugService | None = None,
) -> EvaluationService:
    """
    Construct :class:`~src.infrastructure.adapters.evaluation.evaluation_service.EvaluationService`
    with a fully wired :class:`~src.domain.ports.gold_qa_benchmark_port.GoldQaBenchmarkPort` implementation.
    """
    lj = llm_judge_service if llm_judge_service is not None else LLMJudgeService()
    correlation = correlation_service if correlation_service is not None else CorrelationService()
    failure_analysis = (
        failure_analysis_service if failure_analysis_service is not None else FailureAnalysisService()
    )
    semantic = (
        semantic_similarity_service
        if semantic_similarity_service is not None
        else SemanticSimilarityService()
    )
    explainability = (
        explainability_service if explainability_service is not None else ExplainabilityService()
    )
    auto_debug = auto_debug_service if auto_debug_service is not None else AutoDebugService()

    retrieval_metrics = RetrievalMetricsService()
    answer_quality = AnswerQualityAggregationService()
    row_evaluation = RowEvaluationService(
        retrieval_metrics_service=retrieval_metrics,
        answer_quality_service=answer_quality,
        semantic_similarity_service=semantic,
        llm_judge_service=lj,
    )
    benchmark_execution = BenchmarkExecutionUseCase(
        row_evaluation=row_evaluation,
        aggregation=BenchmarkAggregationService(),
        correlation=correlation,
        failure_analysis=failure_analysis,
        explainability=explainability,
        auto_debug=auto_debug,
    )
    gold_qa = GoldQaBenchmarkAdapter(benchmark_execution)

    return EvaluationService(
        gold_qa_benchmark=gold_qa,
        retrieval_metrics_service=retrieval_metrics,
        answer_quality_service=answer_quality,
    )


__all__ = ["build_evaluation_service"]
