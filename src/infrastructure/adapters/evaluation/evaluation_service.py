from __future__ import annotations

from src.domain.benchmark_result import BenchmarkResult
from src.domain.manual_evaluation_result import ManualEvaluationResult
from src.domain.pipeline_latency import PipelineLatency
from src.domain.pipeline_payloads import PipelineBuildResult
from src.domain.ports.gold_qa_benchmark_port import GoldQaBenchmarkPort
from src.infrastructure.adapters.evaluation.answer_quality_aggregation_service import AnswerQualityAggregationService
from src.infrastructure.adapters.evaluation.retrieval_metrics_service import RetrievalMetricsService

_DEFAULT_RETRIEVAL = RetrievalMetricsService()
_DEFAULT_ANSWER = AnswerQualityAggregationService()


class EvaluationService:
    """
    Evaluation façade: gold-QA runs via injected :class:`~src.domain.ports.gold_qa_benchmark_port.GoldQaBenchmarkPort`
    (wired in :mod:`src.composition.evaluation_wiring`), manual-eval assembly, and shared metric helpers.
    """

    def __init__(
        self,
        *,
        gold_qa_benchmark: GoldQaBenchmarkPort,
        retrieval_metrics_service: RetrievalMetricsService | None = None,
        answer_quality_service: AnswerQualityAggregationService | None = None,
    ) -> None:
        self._gold_qa_benchmark = gold_qa_benchmark
        self._retrieval_metrics = retrieval_metrics_service or RetrievalMetricsService()
        self._answer_quality = answer_quality_service or AnswerQualityAggregationService()

    def evaluate_gold_qa_dataset(
        self,
        *,
        entries,
        pipeline_runner,
    ) -> BenchmarkResult:
        return self._gold_qa_benchmark.evaluate_gold_qa_dataset(
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
        full_latency: PipelineLatency | None,
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
            full_latency=full_latency,
            gold_qa_benchmark=self._gold_qa_benchmark,
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
