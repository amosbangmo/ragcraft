from __future__ import annotations

import logging
import math
import re

import numpy as np

from src.domain.benchmark_result import BenchmarkResult, BenchmarkRow, BenchmarkSummary
from src.domain.pipeline_payloads import PipelineBuildResult
from src.domain.multimodal_metrics import (
    aggregate_multimodal_metrics,
    empty_modality_row_fields,
    modality_row_fields_from_pipeline,
)
from src.services.answer_citation_metrics_service import answer_cited_doc_ids
from src.services.auto_debug_service import AutoDebugService
from src.services.correlation_service import CorrelationService
from src.services.explainability_service import ExplainabilityService
from src.services.failure_analysis_service import FailureAnalysisService
from src.services.llm_judge_service import JUDGE_FAILURE_REASON, LLMJudgeService
from src.services.semantic_similarity_service import SemanticSimilarityService

logger = logging.getLogger(__name__)


def _latency_stage_row_fields(latency: dict | None) -> dict[str, float]:
    if not latency:
        return {
            "query_rewrite_ms": 0.0,
            "retrieval_ms": 0.0,
            "reranking_ms": 0.0,
            "prompt_build_ms": 0.0,
            "answer_generation_ms": 0.0,
        }
    return {
        "query_rewrite_ms": round(float(latency.get("query_rewrite_ms", 0.0)), 2),
        "retrieval_ms": round(float(latency.get("retrieval_ms", 0.0)), 2),
        "reranking_ms": round(float(latency.get("reranking_ms", 0.0)), 2),
        "prompt_build_ms": round(float(latency.get("prompt_build_ms", 0.0)), 2),
        "answer_generation_ms": round(float(latency.get("answer_generation_ms", 0.0)), 2),
    }


def _r2(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 2)


def _mean_round(values: list[float], ndigits: int) -> float | None:
    if not values:
        return None
    return round(float(np.mean(values)), ndigits)


def _rate(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(float(numerator) / float(denominator), 2)


class EvaluationService:
    def __init__(
        self,
        llm_judge_service: object | None = None,
        correlation_service: CorrelationService | None = None,
        failure_analysis_service: FailureAnalysisService | None = None,
        semantic_similarity_service: object | None = None,
        explainability_service: ExplainabilityService | None = None,
        auto_debug_service: AutoDebugService | None = None,
    ):
        # Untyped so tests can inject a stub without coupling to ``LLMJudgeService``.
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

    def _attach_explainability(self, row_payload: dict) -> None:
        explain = self._explainability_service.build_explanation(row_payload)
        row_payload["explanations"] = explain.get("explanations", [])
        row_payload["suggestions"] = explain.get("suggestions", [])

    def evaluate_gold_qa_dataset(
        self,
        *,
        entries,
        pipeline_runner,
    ) -> BenchmarkResult:
        rows: list[BenchmarkRow] = []

        # Retrieval metrics.
        recall_at_k_values: list[float] = []
        source_recall_values: list[float] = []
        precision_at_k_values: list[float] = []
        reciprocal_rank_values: list[float] = []
        average_precision_values: list[float] = []
        confidence_values: list[float] = []
        latency_values: list[float] = []

        # Gold answer overlap (summary focuses on F1).
        answer_f1_values: list[float] = []

        # Prompt doc ID overlap (prompt sources vs gold expectations).
        prompt_doc_id_precision_values: list[float] = []
        prompt_doc_id_recall_values: list[float] = []
        prompt_doc_id_f1_values: list[float] = []

        citation_doc_id_precision_values: list[float] = []
        citation_doc_id_recall_values: list[float] = []
        citation_doc_id_f1_values: list[float] = []

        groundedness_values: list[float] = []
        citation_faithfulness_values: list[float] = []
        answer_relevance_values: list[float] = []
        hallucination_score_values: list[float] = []
        hallucination_flags: list[bool] = []
        answer_correctness_values: list[float] = []
        semantic_similarity_values: list[float] = []
        ndcg_at_k_values: list[float] = []

        entries_with_expected_doc_ids = 0
        entries_with_expected_sources = 0
        entries_with_expected_answers = 0

        doc_id_hits = 0
        source_hits = 0
        prompt_doc_id_hits = 0
        citation_doc_id_hits = 0
        successful_queries = 0

        for entry in entries:
            result = pipeline_runner(entry)
            pipeline = result.get("pipeline")
            answer = (result.get("answer") or "").strip()
            latency_ms = float(result.get("latency_ms", 0.0))
            merged_latency = result.get("latency")
            if not isinstance(merged_latency, dict) and pipeline is not None:
                merged_latency = (
                    pipeline.latency
                    if isinstance(pipeline, PipelineBuildResult)
                    else pipeline.get("latency")
                )
            if not isinstance(merged_latency, dict):
                merged_latency = None

            expected_doc_ids = set(entry.expected_doc_ids or [])
            expected_sources = set(entry.expected_sources or [])
            expected_answer = (entry.expected_answer or "").strip()
            has_expected_answer = bool(expected_answer)

            if expected_doc_ids:
                entries_with_expected_doc_ids += 1

            if expected_sources:
                entries_with_expected_sources += 1

            if expected_answer:
                entries_with_expected_answers += 1

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
                    **_latency_stage_row_fields(merged_latency),
                    "retrieval_mode": "none",
                    "query_rewrite_enabled": False,
                    "hybrid_retrieval_enabled": False,
                    "hallucination_score": None,
                    "has_hallucination": False,
                    "pipeline_failed": True,
                    "judge_failed": False,
                    "groundedness_score": None,
                    "citation_faithfulness_score": None,
                    "answer_relevance_score": None,
                    "answer_correctness_score": None,
                    "semantic_similarity": None,
                    "ndcg_at_k": None,
                    **empty_modality_row_fields(),
                }
                rows.append(
                    BenchmarkRow(
                        entry_id=entry.id,
                        question=entry.question,
                        data=row_payload,
                    )
                )
                latency_values.append(latency_ms)
                continue

            successful_queries += 1

            pl = pipeline.to_dict() if isinstance(pipeline, PipelineBuildResult) else pipeline

            ranked_doc_ids = [
                doc_id
                for doc_id in pl.get("selected_doc_ids", [])
                if doc_id
            ]
            selected_doc_ids = set(ranked_doc_ids)

            prompt_sources = pl.get("prompt_sources", []) or []
            selected_sources = {
                ref.get("source_file")
                for ref in prompt_sources
                if ref.get("source_file")
            }

            # Doc IDs present in the prompt (all assets shown to the model), for prompt_* metrics.
            prompt_source_doc_ids = {
                ref.get("doc_id")
                for ref in prompt_sources
                if ref.get("doc_id")
            }

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
                precision_at_k = self._compute_precision_at_k(
                    ranked_doc_ids=ranked_doc_ids,
                    expected_doc_ids=expected_doc_ids,
                )
                reciprocal_rank = self._compute_reciprocal_rank(
                    ranked_doc_ids=ranked_doc_ids,
                    expected_doc_ids=expected_doc_ids,
                )
                average_precision = self._compute_average_precision(
                    ranked_doc_ids=ranked_doc_ids,
                    expected_doc_ids=expected_doc_ids,
                )
                ndcg_at_k_row = self._compute_ndcg_at_k(
                    ranked_doc_ids=ranked_doc_ids,
                    expected_doc_ids=expected_doc_ids,
                )
                ndcg_at_k_values.append(ndcg_at_k_row)

                recall_at_k_values.append(recall_at_k)
                precision_at_k_values.append(precision_at_k)
                reciprocal_rank_values.append(reciprocal_rank)
                average_precision_values.append(average_precision)

                if doc_id_overlap_count > 0:
                    doc_id_hits += 1

                prompt_doc_id_precision, prompt_doc_id_recall, prompt_doc_id_f1 = (
                    self._compute_set_precision_recall_f1(
                        predicted_values=prompt_source_doc_ids,
                        expected_values=expected_doc_ids,
                    )
                )
                prompt_doc_id_precision_values.append(prompt_doc_id_precision)
                prompt_doc_id_recall_values.append(prompt_doc_id_recall)
                prompt_doc_id_f1_values.append(prompt_doc_id_f1)

                if prompt_doc_id_overlap_count > 0:
                    prompt_doc_id_hits += 1

                citation_doc_id_precision, citation_doc_id_recall, citation_doc_id_f1 = (
                    self._compute_set_precision_recall_f1(
                        predicted_values=answer_cited_doc_id_set,
                        expected_values=expected_doc_ids,
                    )
                )
                citation_doc_id_precision_values.append(citation_doc_id_precision)
                citation_doc_id_recall_values.append(citation_doc_id_recall)
                citation_doc_id_f1_values.append(citation_doc_id_f1)

                if citation_doc_id_overlap_count > 0:
                    citation_doc_id_hits += 1

                hit_at_k_row = 1.0 if doc_id_overlap_count > 0 else 0.0
                prompt_doc_id_hit_rate_row = 1.0 if prompt_doc_id_overlap_count > 0 else 0.0
                citation_doc_id_hit_rate_row = 1.0 if citation_doc_id_overlap_count > 0 else 0.0

            if expected_sources:
                source_recall = source_overlap_count / len(expected_sources)
                source_recall_values.append(source_recall)
                if source_overlap_count > 0:
                    source_hits += 1

            if expected_answer:
                _ap, _ar, answer_f1 = self._compute_answer_precision_recall_f1(
                    generated_answer=answer,
                    expected_answer=expected_answer,
                )

                answer_f1_values.append(answer_f1)
                semantic_similarity_row = self._semantic_similarity_service.compute_similarity(
                    answer,
                    expected_answer,
                )
                semantic_similarity_values.append(semantic_similarity_row)

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
                confidence_values.append(confidence)
            latency_values.append(latency_ms)

            refs_for_judge: list[dict] = []
            if isinstance(prompt_sources, list):
                refs_for_judge = [r for r in prompt_sources if isinstance(r, dict)]

            judge_result = self._llm_judge_service.evaluate(
                question=entry.question,
                answer=result.get("answer", ""),
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
                groundedness_values.append(groundedness)
                citation_faithfulness_values.append(citation_faithfulness)
                answer_relevance_values.append(answer_relevance)
                hallucination_score_values.append(hallucination_score)
                hallucination_flags.append(has_hallucination)
                if has_expected_answer:
                    answer_correctness_values.append(
                        float(getattr(judge_result, "answer_correctness_score", 0.0))
                    )
            ac_row = (
                _r2(float(getattr(judge_result, "answer_correctness_score", 0.0)))
                if has_expected_answer
                else None
            )

            row_payload = {
                "has_expected_answer": has_expected_answer,
                "expected_doc_ids_count": len(expected_doc_ids),
                "retrieved_doc_ids_count": len(selected_doc_ids),
                "doc_id_overlap_count": doc_id_overlap_count,
                "recall_at_k": _r2(recall_at_k),
                "precision_at_k": _r2(precision_at_k),
                "reciprocal_rank": _r2(reciprocal_rank),
                "average_precision": _r2(average_precision),
                "ndcg_at_k": _r2(ndcg_at_k_row),
                "hit_at_k": _r2(hit_at_k_row),
                "prompt_doc_id_hit_rate": _r2(prompt_doc_id_hit_rate_row),
                "citation_doc_id_hit_rate": _r2(citation_doc_id_hit_rate_row),
                "expected_sources_count": len(expected_sources),
                "retrieved_sources_count": len(selected_sources),
                "source_overlap_count": source_overlap_count,
                "source_recall": _r2(source_recall),
                "answer_preview": answer[:240],
                "answer_f1": _r2(answer_f1),
                "semantic_similarity": _r2(semantic_similarity_row),
                "citation_doc_id_precision": _r2(citation_doc_id_precision),
                "citation_doc_id_recall": _r2(citation_doc_id_recall),
                "citation_doc_id_f1": _r2(citation_doc_id_f1),
                "citation_doc_id_overlap_count": citation_doc_id_overlap_count,
                "citation_doc_ids_count": len(answer_cited_doc_id_set),
                "prompt_doc_id_overlap_count": prompt_doc_id_overlap_count,
                "prompt_doc_id_precision": _r2(prompt_doc_id_precision),
                "prompt_doc_id_recall": _r2(prompt_doc_id_recall),
                "prompt_doc_id_f1": _r2(prompt_doc_id_f1),
                "confidence": _r2(confidence),
                "latency_ms": round(latency_ms, 1),
                **_latency_stage_row_fields(merged_latency),
                "retrieval_mode": pl.get("retrieval_mode", "unknown"),
                "query_rewrite_enabled": bool(pl.get("query_rewrite_enabled", False)),
                "hybrid_retrieval_enabled": bool(pl.get("hybrid_retrieval_enabled", False)),
                "hallucination_score": _r2(hallucination_score),
                "has_hallucination": bool(has_hallucination),
                "pipeline_failed": False,
                "judge_failed": judge_failed,
                "groundedness_score": _r2(judge_result.groundedness_score),
                "citation_faithfulness_score": _r2(judge_result.citation_faithfulness_score),
                "answer_relevance_score": _r2(judge_result.answer_relevance_score),
                "answer_correctness_score": ac_row,
                **modality_row_fields_from_pipeline(pl),
            }
            rows.append(
                BenchmarkRow(
                    entry_id=entry.id,
                    question=entry.question,
                    data=row_payload,
                )
            )

        summary_payload = {
            "total_entries": len(rows),
            "successful_queries": successful_queries,
            "entries_with_expected_doc_ids": entries_with_expected_doc_ids,
            "entries_with_expected_sources": entries_with_expected_sources,
            "entries_with_expected_answers": entries_with_expected_answers,
            "avg_recall_at_k": _mean_round(recall_at_k_values, 2),
            "avg_source_recall": _mean_round(source_recall_values, 2),
            "avg_precision_at_k": _mean_round(precision_at_k_values, 2),
            "avg_reciprocal_rank": _mean_round(reciprocal_rank_values, 2),
            "avg_average_precision": _mean_round(average_precision_values, 2),
            "avg_ndcg_at_k": _mean_round(ndcg_at_k_values, 2),
            "avg_confidence": _mean_round(confidence_values, 2),
            "avg_latency_ms": _mean_round(latency_values, 1),
            "pipeline_failure_rate": _rate(len(rows) - successful_queries, len(rows)),
            "hit_at_k": _rate(doc_id_hits, entries_with_expected_doc_ids),
            "source_hit_rate": _rate(source_hits, entries_with_expected_sources),
            "avg_answer_f1": _mean_round(answer_f1_values, 2),
            "avg_semantic_similarity": _mean_round(semantic_similarity_values, 2),
            "avg_prompt_doc_id_precision": _mean_round(prompt_doc_id_precision_values, 2),
            "avg_prompt_doc_id_recall": _mean_round(prompt_doc_id_recall_values, 2),
            "avg_prompt_doc_id_f1": _mean_round(prompt_doc_id_f1_values, 2),
            "prompt_doc_id_hit_rate": _rate(prompt_doc_id_hits, entries_with_expected_doc_ids),
            "avg_citation_doc_id_precision": _mean_round(citation_doc_id_precision_values, 2),
            "avg_citation_doc_id_recall": _mean_round(citation_doc_id_recall_values, 2),
            "avg_citation_doc_id_f1": _mean_round(citation_doc_id_f1_values, 2),
            "citation_doc_id_hit_rate": _rate(citation_doc_id_hits, entries_with_expected_doc_ids),
            "avg_groundedness_score": _mean_round(groundedness_values, 2),
            "avg_citation_faithfulness_score": _mean_round(citation_faithfulness_values, 2),
            "avg_answer_relevance_score": _mean_round(answer_relevance_values, 2),
            "avg_answer_correctness": _mean_round(answer_correctness_values, 2),
            "avg_hallucination_score": _mean_round(hallucination_score_values, 2),
            "hallucination_rate": (
                round(
                    sum(1 for flag in hallucination_flags if flag) / len(hallucination_flags),
                    2,
                )
                if hallucination_flags
                else None
            ),
        }

        failed_queries = len(rows) - successful_queries
        logger.info(
            "Evaluation summary: %s/%s successful queries (%s pipeline failures)",
            successful_queries,
            len(rows),
            failed_queries,
        )
        if hallucination_flags:
            logger.info(
                "Evaluation: hallucination flag rate=%s",
                summary_payload.get("hallucination_rate"),
            )
        if groundedness_values:
            low_g = sum(1 for g in groundedness_values if float(g) < 0.5)
            logger.info(
                "Evaluation: %s/%s successful rows with groundedness_score < 0.5",
                low_g,
                len(groundedness_values),
            )
        retr_low = 0
        retr_den = 0
        for r in rows:
            d = r.data
            ex = int(d.get("expected_doc_ids_count") or 0)
            rc = d.get("recall_at_k")
            if ex > 0 and rc is not None:
                retr_den += 1
                if float(rc) < 0.5:
                    retr_low += 1
        if retr_den > 0:
            logger.info(
                "Evaluation: recall@k < 0.5 on %s/%s rows with expected doc IDs",
                retr_low,
                retr_den,
            )

        correlation_rows = [dict(r.data) for r in rows]
        correlations = self._correlation_service.compute(correlation_rows)

        row_dicts = [row.to_dict() for row in rows]
        failure_full = self._failure_analysis_service.analyze(row_dicts)
        row_failure_meta = failure_full.get("row_failures") or []
        failures_report = {k: v for k, v in failure_full.items() if k != "row_failures"}

        rebuilt: list[BenchmarkRow] = []
        for idx, row in enumerate(rows):
            meta = row_failure_meta[idx] if idx < len(row_failure_meta) else {}
            labels = meta.get("failure_labels") if isinstance(meta, dict) else None
            crit = meta.get("failure_critical") if isinstance(meta, dict) else None
            if not isinstance(labels, list):
                labels = []
            d = dict(row.data)
            d["failure_labels"] = list(labels)
            d["failure_critical"] = bool(crit) if crit is not None else False
            self._attach_explainability(d)
            rebuilt.append(
                BenchmarkRow(entry_id=row.entry_id, question=row.question, data=d)
            )

        row_dicts_final = [row.to_dict() for row in rebuilt]
        mm_raw = aggregate_multimodal_metrics(row_dicts_final)
        multimodal_metrics = None
        if mm_raw and mm_raw.get("has_multimodal_assets"):
            multimodal_metrics = dict(mm_raw)

        auto_debug = self._auto_debug_service.build_suggestions(
            summary_payload,
            failures_report,
        )

        return BenchmarkResult(
            summary=BenchmarkSummary(data=summary_payload),
            rows=rebuilt,
            correlations=correlations,
            failures=failures_report,
            multimodal_metrics=multimodal_metrics,
            auto_debug=auto_debug,
        )

    def _compute_ndcg_at_k(
        self,
        *,
        ranked_doc_ids: list[str],
        expected_doc_ids: set[str],
    ) -> float:
        """
        NDCG over the full ranked list (K = len(ranked_doc_ids)).
        Binary relevance: 1 if doc_id is in expected_doc_ids, else 0.
        DCG uses sum(rel / log2(rank + 1)) for 1-based rank.
        """
        if not ranked_doc_ids or not expected_doc_ids:
            return 0.0

        def _dcg(relevances: list[float]) -> float:
            total = 0.0
            for i, rel in enumerate(relevances):
                rank = i + 1
                total += rel / math.log2(rank + 1)
            return total

        rel = [1.0 if doc_id in expected_doc_ids else 0.0 for doc_id in ranked_doc_ids]
        dcg_score = _dcg(rel)
        ideal = sorted(rel, reverse=True)
        idcg = _dcg(ideal)
        if idcg <= 0.0:
            return 0.0
        return dcg_score / idcg

    def _compute_precision_at_k(
        self,
        *,
        ranked_doc_ids: list[str],
        expected_doc_ids: set[str],
    ) -> float:
        if not ranked_doc_ids:
            return 0.0

        relevant_retrieved = sum(1 for doc_id in ranked_doc_ids if doc_id in expected_doc_ids)
        return relevant_retrieved / len(ranked_doc_ids)

    def _compute_reciprocal_rank(
        self,
        *,
        ranked_doc_ids: list[str],
        expected_doc_ids: set[str],
    ) -> float:
        for index, doc_id in enumerate(ranked_doc_ids, start=1):
            if doc_id in expected_doc_ids:
                return 1.0 / index
        return 0.0

    def _compute_average_precision(
        self,
        *,
        ranked_doc_ids: list[str],
        expected_doc_ids: set[str],
    ) -> float:
        if not ranked_doc_ids or not expected_doc_ids:
            return 0.0

        precision_sum = 0.0
        relevant_found = 0

        for index, doc_id in enumerate(ranked_doc_ids, start=1):
            if doc_id not in expected_doc_ids:
                continue

            relevant_found += 1
            precision_at_index = relevant_found / index
            precision_sum += precision_at_index

        if relevant_found == 0:
            return 0.0

        return precision_sum / len(expected_doc_ids)

    def _normalize_text(self, text: str) -> str:
        normalized = re.sub(r"\s+", " ", (text or "").strip().lower())
        normalized = re.sub(r"[^a-z0-9àâçéèêëîïôûùüÿñæœ\s_-]", "", normalized)
        return normalized.strip()

    def _tokenize_text(self, text: str) -> list[str]:
        normalized = self._normalize_text(text)
        if not normalized:
            return []
        return [token for token in normalized.split(" ") if token]

    def _compute_answer_precision_recall_f1(
        self,
        *,
        generated_answer: str,
        expected_answer: str,
    ) -> tuple[float, float, float]:
        generated_tokens = self._tokenize_text(generated_answer)
        expected_tokens = self._tokenize_text(expected_answer)

        if not generated_tokens or not expected_tokens:
            return 0.0, 0.0, 0.0

        generated_counts: dict[str, int] = {}
        expected_counts: dict[str, int] = {}

        for token in generated_tokens:
            generated_counts[token] = generated_counts.get(token, 0) + 1

        for token in expected_tokens:
            expected_counts[token] = expected_counts.get(token, 0) + 1

        overlap = 0
        for token, count in generated_counts.items():
            overlap += min(count, expected_counts.get(token, 0))

        if overlap == 0:
            return 0.0, 0.0, 0.0

        precision = overlap / len(generated_tokens)
        recall = overlap / len(expected_tokens)

        if precision + recall == 0:
            f1 = 0.0
        else:
            f1 = 2 * precision * recall / (precision + recall)

        return precision, recall, f1

    def _compute_set_precision_recall_f1(
        self,
        *,
        predicted_values: set[str],
        expected_values: set[str],
    ) -> tuple[float, float, float]:
        if not expected_values:
            return 0.0, 0.0, 0.0

        if not predicted_values:
            return 0.0, 0.0, 0.0

        overlap = len(predicted_values.intersection(expected_values))

        precision = overlap / len(predicted_values) if predicted_values else 0.0
        recall = overlap / len(expected_values) if expected_values else 0.0

        if precision + recall == 0:
            f1 = 0.0
        else:
            f1 = 2 * precision * recall / (precision + recall)

        return precision, recall, f1
