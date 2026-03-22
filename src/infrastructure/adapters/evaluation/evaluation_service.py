from __future__ import annotations

from src.application.use_cases.evaluation.benchmark_execution import BenchmarkExecutionUseCase
from src.domain.benchmark_result import BenchmarkResult
from src.domain.manual_evaluation_result import ManualEvaluationResult
from src.domain.pipeline_payloads import PipelineBuildResult
from src.infrastructure.adapters.evaluation.answer_quality_aggregation_service import AnswerQualityAggregationService
from src.infrastructure.adapters.evaluation.auto_debug_service import AutoDebugService
from src.infrastructure.adapters.evaluation.benchmark_aggregation_service import BenchmarkAggregationService
from src.infrastructure.adapters.evaluation.correlation_service import CorrelationService
from src.infrastructure.adapters.evaluation.explainability_service import ExplainabilityService
from src.infrastructure.adapters.evaluation.failure_analysis_service import FailureAnalysisService
from src.infrastructure.adapters.evaluation.retrieval_metrics_service import RetrievalMetricsService
from src.infrastructure.adapters.evaluation.row_evaluation_service import RowEvaluationService
from src.infrastructure.adapters.evaluation.semantic_similarity_service import SemanticSimilarityService
from src.infrastructure.adapters.evaluation.llm_judge_service import LLMJudgeService

_DEFAULT_RETRIEVAL = RetrievalMetricsService()
_DEFAULT_ANSWER = AnswerQualityAggregationService()


class EvaluationService:
    """
    Façade for gold QA benchmark evaluation. Delegates orchestration to
    :class:`~src.application.use_cases.evaluation.benchmark_execution.BenchmarkExecutionUseCase`
    and composes focused metric / row services.
    """

    def __init__(
        self,
        llm_judge_service: object | None = None,
        correlation_service: CorrelationService | None = None,
        failure_analysis_service: FailureAnalysisService | None = None,
        semantic_similarity_service: object | None = None,
        explainability_service: ExplainabilityService | None = None,
        auto_debug_service: AutoDebugService | None = None,
    ):
        self._llm_judge_service = (
            llm_judge_service if llm_judge_service is not None else LLMJudgeService()
        )
        self._correlation_service = (
            correlation_service if correlation_service is not None else CorrelationService()
        )
        self._failure_analysis_service = (
            failure_analysis_service
            if failure_analysis_service is not None
            else FailureAnalysisService()
        )
        self._semantic_similarity_service = (
            semantic_similarity_service
            if semantic_similarity_service is not None
            else SemanticSimilarityService()
        )
        self._explainability_service = (
            explainability_service
            if explainability_service is not None
            else ExplainabilityService()
        )
        self._auto_debug_service = (
            auto_debug_service if auto_debug_service is not None else AutoDebugService()
        )

        self._retrieval_metrics = RetrievalMetricsService()
        self._answer_quality = AnswerQualityAggregationService()
        self._row_evaluation = RowEvaluationService(
            retrieval_metrics_service=self._retrieval_metrics,
            answer_quality_service=self._answer_quality,
            semantic_similarity_service=self._semantic_similarity_service,
            llm_judge_service=self._llm_judge_service,
        )
        self._benchmark_execution = BenchmarkExecutionUseCase(
            row_evaluation=self._row_evaluation,
            aggregation=BenchmarkAggregationService(),
            correlation=self._correlation_service,
            failure_analysis=self._failure_analysis_service,
            explainability=self._explainability_service,
            auto_debug=self._auto_debug_service,
        )

    def evaluate_gold_qa_dataset(
        self,
        *,
        entries,
        pipeline_runner,
    ) -> BenchmarkResult:
        return self._benchmark_execution.execute(
            entries=entries,
            pipeline_runner=pipeline_runner,
        )

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
        full_latency_dict: dict[str, float] | None,
    ) -> ManualEvaluationResult:
        from src.infrastructure.adapters.evaluation.manual_evaluation_service import (
            manual_evaluation_result_from_rag_outputs,
        )

        return manual_evaluation_result_from_rag_outputs(
            user_id=user_id,
            project_id=project_id,
            q=question,
            exp_ans=expected_answer,
            exp_docs=list(expected_doc_ids),
            exp_src=list(expected_sources),
            pipeline=pipeline,
            answer=answer,
            latency_ms=latency_ms,
            full_latency_dict=full_latency_dict,
            evaluation_service=self,
        )

    def _retrieval(self) -> RetrievalMetricsService:
        return self.__dict__.get("_retrieval_metrics") or _DEFAULT_RETRIEVAL

    def _answer(self) -> AnswerQualityAggregationService:
        return self.__dict__.get("_answer_quality") or _DEFAULT_ANSWER

    def _compute_ndcg_at_k(self, **kwargs):
        return self._retrieval().compute_ndcg_at_k(**kwargs)

    def _compute_precision_at_k(self, **kwargs):
        return self._retrieval().compute_precision_at_k(**kwargs)

    def _compute_reciprocal_rank(self, **kwargs):
        return self._retrieval().compute_reciprocal_rank(**kwargs)

    def _compute_average_precision(self, **kwargs):
        return self._retrieval().compute_average_precision(**kwargs)

    def _compute_set_precision_recall_f1(self, **kwargs):
        return self._retrieval().compute_set_precision_recall_f1(**kwargs)

    def _compute_answer_precision_recall_f1(self, **kwargs):
        return self._answer().compute_answer_precision_recall_f1(**kwargs)

    def _normalize_text(self, text: str) -> str:
        return self._answer().normalize_text(text)

    def _tokenize_text(self, text: str) -> list[str]:
        return self._answer().tokenize_text(text)
