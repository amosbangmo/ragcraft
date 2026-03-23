"""Build a single gold-QA benchmark row (pipeline success or failure) and update run accumulators."""

from __future__ import annotations

from domain.evaluation.benchmark_accumulator import BenchmarkAccumulator
from domain.evaluation.benchmark_math import latency_stage_row_fields, r2
from domain.evaluation.benchmark_result import BenchmarkRow
from domain.evaluation.gold_qa_row_input import GoldQaPipelineRowInput
from domain.evaluation.judge_metrics_row import EvaluationJudgeMetricsRow
from domain.evaluation.multimodal_metrics import (
    empty_modality_row_fields,
    modality_row_fields_from_pipeline,
)
from domain.rag.pipeline_latency import PipelineLatency
from domain.rag.pipeline_payloads import PipelineBuildResult
from infrastructure.evaluation.answer_citation_metrics_service import (
    answer_cited_doc_ids,
)
from infrastructure.evaluation.answer_quality_aggregation_service import (
    AnswerQualityAggregationService,
)
from infrastructure.evaluation.llm_judge_service import JUDGE_FAILURE_REASON
from infrastructure.evaluation.retrieval_metrics_service import RetrievalMetricsService


def judge_row_fields(
    judge_result: object,
    *,
    judge_failed: bool,
    has_expected_answer: bool,
) -> dict[str, object]:
    return EvaluationJudgeMetricsRow.from_judge_result(
        judge_result,
        judge_failed=judge_failed,
        has_expected_answer=has_expected_answer,
        failure_reason_fallback=JUDGE_FAILURE_REASON,
    ).to_row_fragment()


class RowEvaluationService:
    def __init__(
        self,
        *,
        retrieval_metrics_service: RetrievalMetricsService,
        answer_quality_service: AnswerQualityAggregationService,
        semantic_similarity_service: object,
        llm_judge_service: object,
    ) -> None:
        self._retrieval = retrieval_metrics_service
        self._answer_quality = answer_quality_service
        self._semantic_similarity_service = semantic_similarity_service
        self._llm_judge_service = llm_judge_service

    def process_row(self, entry, result: GoldQaPipelineRowInput, acc: BenchmarkAccumulator) -> None:
        pipeline = result.pipeline
        answer = (result.answer or "").strip()
        latency_ms = float(result.latency_ms)
        merged_latency: PipelineLatency | None = result.full_latency
        if merged_latency is None and pipeline is not None:
            merged_latency = pipeline.latency

        expected_doc_ids = set(entry.expected_doc_ids or [])
        expected_sources = set(entry.expected_sources or [])
        expected_answer = (entry.expected_answer or "").strip()
        has_expected_answer = bool(expected_answer)

        if expected_doc_ids:
            acc.entries_with_expected_doc_ids += 1

        if expected_sources:
            acc.entries_with_expected_sources += 1

        if expected_answer:
            acc.entries_with_expected_answers += 1

        if pipeline is None:
            row_payload = {
                "has_expected_answer": has_expected_answer,
                "expected_doc_ids_count": len(expected_doc_ids),
                "retrieved_doc_ids_count": 0,
                "doc_id_overlap_count": 0,
                "recall_at_k": None,
                "precision_at_k": None,
                "reciprocal_rank": None,
                "average_precision": None,
                "hit_at_k": None,
                "prompt_doc_id_hit_rate": None,
                "citation_doc_id_hit_rate": None,
                "expected_sources_count": len(expected_sources),
                "retrieved_sources_count": 0,
                "source_overlap_count": 0,
                "source_recall": None,
                "answer_preview": "",
                "answer_f1": None,
                "citation_doc_id_precision": None,
                "citation_doc_id_recall": None,
                "citation_doc_id_f1": None,
                "citation_doc_id_overlap_count": 0,
                "citation_doc_ids_count": 0,
                "prompt_doc_id_overlap_count": 0,
                "prompt_doc_id_precision": None,
                "prompt_doc_id_recall": None,
                "prompt_doc_id_f1": None,
                "confidence": None,
                "latency_ms": round(latency_ms, 1),
                **latency_stage_row_fields(merged_latency),
                "retrieval_mode": "none",
                "query_rewrite_enabled": False,
                "hybrid_retrieval_enabled": False,
                "hallucination_score": None,
                "has_hallucination": False,
                "pipeline_failed": True,
                "judge_failed": False,
                "judge_failure_reason": None,
                "groundedness_score": None,
                "citation_faithfulness_score": None,
                "answer_relevance_score": None,
                "answer_correctness_score": None,
                "semantic_similarity": None,
                "ndcg_at_k": None,
                **empty_modality_row_fields(),
            }
            acc.rows.append(
                BenchmarkRow(
                    entry_id=entry.id,
                    question=entry.question,
                    data=row_payload,
                )
            )
            acc.latency_values.append(latency_ms)
            return

        acc.successful_queries += 1

        pl = pipeline.to_dict() if isinstance(pipeline, PipelineBuildResult) else pipeline

        ranked_doc_ids = [doc_id for doc_id in pl.get("selected_doc_ids", []) if doc_id]
        selected_doc_ids = set(ranked_doc_ids)

        prompt_sources = pl.get("prompt_sources", []) or []
        selected_sources = {
            ref.get("source_file") for ref in prompt_sources if ref.get("source_file")
        }

        prompt_source_doc_ids = {ref.get("doc_id") for ref in prompt_sources if ref.get("doc_id")}

        answer_cited_doc_id_set = answer_cited_doc_ids(
            answer=answer,
            prompt_sources=prompt_sources,
        )

        doc_id_overlap_count = len(selected_doc_ids.intersection(expected_doc_ids))
        source_overlap_count = len(selected_sources.intersection(expected_sources))

        prompt_doc_id_overlap_count = len(prompt_source_doc_ids.intersection(expected_doc_ids))
        citation_doc_id_overlap_count = len(answer_cited_doc_id_set.intersection(expected_doc_ids))

        recall_at_k = None
        source_recall = None
        precision_at_k = None
        reciprocal_rank = None
        average_precision = None

        answer_f1 = None

        prompt_doc_id_precision = None
        prompt_doc_id_recall = None
        prompt_doc_id_f1 = None

        citation_doc_id_precision = None
        citation_doc_id_recall = None
        citation_doc_id_f1 = None

        hit_at_k_row = None
        prompt_doc_id_hit_rate_row = None
        citation_doc_id_hit_rate_row = None

        ndcg_at_k_row = None
        semantic_similarity_row = None

        if expected_doc_ids:
            recall_at_k = doc_id_overlap_count / len(expected_doc_ids)
            precision_at_k = self._retrieval.compute_precision_at_k(
                ranked_doc_ids=ranked_doc_ids,
                expected_doc_ids=expected_doc_ids,
            )
            reciprocal_rank = self._retrieval.compute_reciprocal_rank(
                ranked_doc_ids=ranked_doc_ids,
                expected_doc_ids=expected_doc_ids,
            )
            average_precision = self._retrieval.compute_average_precision(
                ranked_doc_ids=ranked_doc_ids,
                expected_doc_ids=expected_doc_ids,
            )
            ndcg_at_k_row = self._retrieval.compute_ndcg_at_k(
                ranked_doc_ids=ranked_doc_ids,
                expected_doc_ids=expected_doc_ids,
            )
            acc.ndcg_at_k_values.append(ndcg_at_k_row)

            acc.recall_at_k_values.append(recall_at_k)
            acc.precision_at_k_values.append(precision_at_k)
            acc.reciprocal_rank_values.append(reciprocal_rank)
            acc.average_precision_values.append(average_precision)

            if doc_id_overlap_count > 0:
                acc.doc_id_hits += 1

            prompt_doc_id_precision, prompt_doc_id_recall, prompt_doc_id_f1 = (
                self._retrieval.compute_set_precision_recall_f1(
                    predicted_values=prompt_source_doc_ids,
                    expected_values=expected_doc_ids,
                )
            )
            acc.prompt_doc_id_precision_values.append(prompt_doc_id_precision)
            acc.prompt_doc_id_recall_values.append(prompt_doc_id_recall)
            acc.prompt_doc_id_f1_values.append(prompt_doc_id_f1)

            if prompt_doc_id_overlap_count > 0:
                acc.prompt_doc_id_hits += 1

            citation_doc_id_precision, citation_doc_id_recall, citation_doc_id_f1 = (
                self._retrieval.compute_set_precision_recall_f1(
                    predicted_values=answer_cited_doc_id_set,
                    expected_values=expected_doc_ids,
                )
            )
            acc.citation_doc_id_precision_values.append(citation_doc_id_precision)
            acc.citation_doc_id_recall_values.append(citation_doc_id_recall)
            acc.citation_doc_id_f1_values.append(citation_doc_id_f1)

            if citation_doc_id_overlap_count > 0:
                acc.citation_doc_id_hits += 1

            hit_at_k_row = 1.0 if doc_id_overlap_count > 0 else 0.0
            prompt_doc_id_hit_rate_row = 1.0 if prompt_doc_id_overlap_count > 0 else 0.0
            citation_doc_id_hit_rate_row = 1.0 if citation_doc_id_overlap_count > 0 else 0.0

        if expected_sources:
            source_recall = source_overlap_count / len(expected_sources)
            acc.source_recall_values.append(source_recall)
            if source_overlap_count > 0:
                acc.source_hits += 1

        if expected_answer:
            _ap, _ar, answer_f1 = self._answer_quality.compute_answer_precision_recall_f1(
                generated_answer=answer,
                expected_answer=expected_answer,
            )

            acc.answer_f1_values.append(answer_f1)
            semantic_similarity_row = self._semantic_similarity_service.compute_similarity(
                answer,
                expected_answer,
            )
            acc.semantic_similarity_values.append(semantic_similarity_row)

        confidence_raw = pl.get("confidence")
        confidence: float | None
        if confidence_raw is None:
            confidence = None
        else:
            try:
                confidence = float(confidence_raw)
            except (TypeError, ValueError):
                confidence = None
        if confidence is not None:
            acc.confidence_values.append(confidence)
        acc.latency_values.append(latency_ms)

        refs_for_judge: list[dict] = []
        if isinstance(prompt_sources, list):
            refs_for_judge = [r for r in prompt_sources if isinstance(r, dict)]

        judge_result = self._llm_judge_service.evaluate(
            question=entry.question,
            answer=result.answer,
            raw_context=pl.get("raw_context", ""),
            prompt_sources=refs_for_judge,
            expected_answer=expected_answer if has_expected_answer else None,
        )
        judge_failed = getattr(judge_result, "reason", None) == JUDGE_FAILURE_REASON
        groundedness = judge_result.groundedness_score
        citation_faithfulness = judge_result.citation_faithfulness_score
        answer_relevance = judge_result.answer_relevance_score
        hallucination_score = judge_result.hallucination_score
        has_hallucination = judge_result.has_hallucination

        if not judge_failed:
            acc.groundedness_values.append(groundedness)
            acc.citation_faithfulness_values.append(citation_faithfulness)
            acc.answer_relevance_values.append(answer_relevance)
            acc.hallucination_score_values.append(hallucination_score)
            acc.hallucination_flags.append(has_hallucination)
            if has_expected_answer:
                acc.answer_correctness_values.append(
                    float(getattr(judge_result, "answer_correctness_score", 0.0))
                )

        jfields = judge_row_fields(
            judge_result,
            judge_failed=judge_failed,
            has_expected_answer=has_expected_answer,
        )

        row_payload = {
            "has_expected_answer": has_expected_answer,
            "expected_doc_ids_count": len(expected_doc_ids),
            "retrieved_doc_ids_count": len(selected_doc_ids),
            "doc_id_overlap_count": doc_id_overlap_count,
            "recall_at_k": r2(recall_at_k),
            "precision_at_k": r2(precision_at_k),
            "reciprocal_rank": r2(reciprocal_rank),
            "average_precision": r2(average_precision),
            "ndcg_at_k": r2(ndcg_at_k_row),
            "hit_at_k": r2(hit_at_k_row),
            "prompt_doc_id_hit_rate": r2(prompt_doc_id_hit_rate_row),
            "citation_doc_id_hit_rate": r2(citation_doc_id_hit_rate_row),
            "expected_sources_count": len(expected_sources),
            "retrieved_sources_count": len(selected_sources),
            "source_overlap_count": source_overlap_count,
            "source_recall": r2(source_recall),
            "answer_preview": answer[:240],
            "answer_f1": r2(answer_f1),
            "semantic_similarity": r2(semantic_similarity_row),
            "citation_doc_id_precision": r2(citation_doc_id_precision),
            "citation_doc_id_recall": r2(citation_doc_id_recall),
            "citation_doc_id_f1": r2(citation_doc_id_f1),
            "citation_doc_id_overlap_count": citation_doc_id_overlap_count,
            "citation_doc_ids_count": len(answer_cited_doc_id_set),
            "prompt_doc_id_overlap_count": prompt_doc_id_overlap_count,
            "prompt_doc_id_precision": r2(prompt_doc_id_precision),
            "prompt_doc_id_recall": r2(prompt_doc_id_recall),
            "prompt_doc_id_f1": r2(prompt_doc_id_f1),
            "confidence": r2(confidence),
            "latency_ms": round(latency_ms, 1),
            **latency_stage_row_fields(merged_latency),
            "retrieval_mode": pl.get("retrieval_mode", "unknown"),
            "query_rewrite_enabled": bool(pl.get("query_rewrite_enabled", False)),
            "hybrid_retrieval_enabled": bool(pl.get("hybrid_retrieval_enabled", False)),
            "pipeline_failed": False,
            "judge_failed": judge_failed,
            **jfields,
            **modality_row_fields_from_pipeline(pl),
        }
        acc.rows.append(
            BenchmarkRow(
                entry_id=entry.id,
                question=entry.question,
                data=row_payload,
            )
        )
