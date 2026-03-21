from __future__ import annotations

import re

import numpy as np

from src.domain.benchmark_result import BenchmarkResult, BenchmarkRow, BenchmarkSummary
from src.domain.pipeline_payloads import PipelineBuildResult
from src.domain.multimodal_metrics import (
    aggregate_multimodal_metrics,
    empty_modality_row_fields,
    modality_row_fields_from_pipeline,
)
from src.services.correlation_service import CorrelationService
from src.services.failure_analysis_service import FailureAnalysisService
from src.services.llm_judge_service import LLMJudgeService


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


class EvaluationService:
    def __init__(
        self,
        llm_judge_service: object | None = None,
        correlation_service: CorrelationService | None = None,
        failure_analysis_service: FailureAnalysisService | None = None,
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

        # Answer correctness metrics.
        answer_exact_match_values: list[float] = []
        answer_precision_values: list[float] = []
        answer_recall_values: list[float] = []
        answer_f1_values: list[float] = []

        # Prompt-source overlap metrics (vs gold expectations).
        prompt_doc_id_precision_values: list[float] = []
        prompt_doc_id_recall_values: list[float] = []
        prompt_doc_id_f1_values: list[float] = []
        prompt_source_precision_values: list[float] = []
        prompt_source_recall_values: list[float] = []
        prompt_source_f1_values: list[float] = []

        groundedness_values: list[float] = []
        prompt_source_alignment_values: list[float] = []
        answer_relevance_values: list[float] = []
        hallucination_score_values: list[float] = []
        hallucination_flags: list[bool] = []

        entries_with_expected_doc_ids = 0
        entries_with_expected_sources = 0
        entries_with_expected_answers = 0

        doc_id_hits = 0
        source_hits = 0
        prompt_doc_id_hits = 0
        prompt_source_hits = 0
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
                    "recall_at_k": 0.0,
                    "precision_at_k": 0.0,
                    "reciprocal_rank": 0.0,
                    "average_precision": 0.0,
                    "expected_sources_count": len(expected_sources),
                    "retrieved_sources_count": 0,
                    "source_overlap_count": 0,
                    "source_recall": 0.0,
                    "answer_preview": "",
                    "answer_exact_match": 0.0,
                    "answer_precision": 0.0,
                    "answer_recall": 0.0,
                    "answer_f1": 0.0,
                    "cited_doc_ids_count": 0,
                    "prompt_doc_id_overlap_count": 0,
                    "prompt_doc_id_precision": 0.0,
                    "prompt_doc_id_recall": 0.0,
                    "prompt_doc_id_f1": 0.0,
                    "cited_sources_count": 0,
                    "prompt_source_overlap_count": 0,
                    "prompt_source_precision": 0.0,
                    "prompt_source_recall": 0.0,
                    "prompt_source_f1": 0.0,
                    "confidence": 0.0,
                    "latency_ms": round(latency_ms, 1),
                    **_latency_stage_row_fields(merged_latency),
                    "retrieval_mode": "none",
                    "query_rewrite_enabled": False,
                    "hybrid_retrieval_enabled": False,
                    "groundedness": 0.0,
                    "prompt_source_alignment": 0.0,
                    "answer_relevance": 0.0,
                    "hallucination_score": 0.0,
                    "has_hallucination": True,
                    "groundedness_score": 0.0,
                    "prompt_source_alignment_score": 0.0,
                    "answer_relevance_score": 0.0,
                    **empty_modality_row_fields(),
                }
                rows.append(
                    BenchmarkRow(
                        entry_id=entry.id,
                        question=entry.question,
                        data=row_payload,
                    )
                )
                groundedness_values.append(0.0)
                prompt_source_alignment_values.append(0.0)
                answer_relevance_values.append(0.0)
                hallucination_score_values.append(0.0)
                hallucination_flags.append(True)
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

            # Doc/source sets for prompt-source overlap metrics are intentionally derived
            # from the explicit prompt source objects. This distinguishes selected prompt
            # assets from any future answer-surface citation parsing.
            cited_doc_ids = {
                ref.get("doc_id")
                for ref in prompt_sources
                if ref.get("doc_id")
            }
            cited_sources = {
                ref.get("source_file")
                for ref in prompt_sources
                if ref.get("source_file")
            }

            doc_id_overlap_count = len(selected_doc_ids.intersection(expected_doc_ids))
            source_overlap_count = len(selected_sources.intersection(expected_sources))

            prompt_doc_id_overlap_count = len(cited_doc_ids.intersection(expected_doc_ids))
            prompt_source_overlap_count = len(cited_sources.intersection(expected_sources))

            recall_at_k = 0.0
            source_recall = 0.0
            precision_at_k = 0.0
            reciprocal_rank = 0.0
            average_precision = 0.0

            answer_exact_match = 0.0
            answer_precision = 0.0
            answer_recall = 0.0
            answer_f1 = 0.0

            prompt_doc_id_precision = 0.0
            prompt_doc_id_recall = 0.0
            prompt_doc_id_f1 = 0.0
            prompt_source_precision = 0.0
            prompt_source_recall = 0.0
            prompt_source_f1 = 0.0

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

                recall_at_k_values.append(recall_at_k)
                precision_at_k_values.append(precision_at_k)
                reciprocal_rank_values.append(reciprocal_rank)
                average_precision_values.append(average_precision)

                if doc_id_overlap_count > 0:
                    doc_id_hits += 1

                prompt_doc_id_precision, prompt_doc_id_recall, prompt_doc_id_f1 = (
                    self._compute_set_precision_recall_f1(
                        predicted_values=cited_doc_ids,
                        expected_values=expected_doc_ids,
                    )
                )
                prompt_doc_id_precision_values.append(prompt_doc_id_precision)
                prompt_doc_id_recall_values.append(prompt_doc_id_recall)
                prompt_doc_id_f1_values.append(prompt_doc_id_f1)

                if prompt_doc_id_overlap_count > 0:
                    prompt_doc_id_hits += 1

            if expected_sources:
                source_recall = source_overlap_count / len(expected_sources)
                source_recall_values.append(source_recall)
                if source_overlap_count > 0:
                    source_hits += 1

                prompt_source_precision, prompt_source_recall, prompt_source_f1 = (
                    self._compute_set_precision_recall_f1(
                        predicted_values=cited_sources,
                        expected_values=expected_sources,
                    )
                )
                prompt_source_precision_values.append(prompt_source_precision)
                prompt_source_recall_values.append(prompt_source_recall)
                prompt_source_f1_values.append(prompt_source_f1)

                if prompt_source_overlap_count > 0:
                    prompt_source_hits += 1

            if expected_answer:
                answer_exact_match = self._compute_answer_exact_match(
                    generated_answer=answer,
                    expected_answer=expected_answer,
                )
                answer_precision, answer_recall, answer_f1 = self._compute_answer_precision_recall_f1(
                    generated_answer=answer,
                    expected_answer=expected_answer,
                )

                answer_exact_match_values.append(answer_exact_match)
                answer_precision_values.append(answer_precision)
                answer_recall_values.append(answer_recall)
                answer_f1_values.append(answer_f1)

            confidence = float(pl.get("confidence", 0.0))
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
            )
            groundedness = judge_result.groundedness_score
            prompt_source_alignment = judge_result.prompt_source_alignment_score
            answer_relevance = judge_result.answer_relevance_score
            hallucination_score = judge_result.hallucination_score
            has_hallucination = judge_result.has_hallucination

            groundedness_values.append(groundedness)
            prompt_source_alignment_values.append(prompt_source_alignment)
            answer_relevance_values.append(answer_relevance)
            hallucination_score_values.append(hallucination_score)
            hallucination_flags.append(has_hallucination)

            row_payload = {
                "has_expected_answer": has_expected_answer,
                "expected_doc_ids_count": len(expected_doc_ids),
                "retrieved_doc_ids_count": len(selected_doc_ids),
                "doc_id_overlap_count": doc_id_overlap_count,
                "recall_at_k": round(recall_at_k, 2),
                "precision_at_k": round(precision_at_k, 2),
                "reciprocal_rank": round(reciprocal_rank, 2),
                "average_precision": round(average_precision, 2),
                "expected_sources_count": len(expected_sources),
                "retrieved_sources_count": len(selected_sources),
                "source_overlap_count": source_overlap_count,
                "source_recall": round(source_recall, 2),
                "answer_preview": answer[:240],
                "answer_exact_match": round(answer_exact_match, 2),
                "answer_precision": round(answer_precision, 2),
                "answer_recall": round(answer_recall, 2),
                "answer_f1": round(answer_f1, 2),
                "cited_doc_ids_count": len(cited_doc_ids),
                "prompt_doc_id_overlap_count": prompt_doc_id_overlap_count,
                "prompt_doc_id_precision": round(prompt_doc_id_precision, 2),
                "prompt_doc_id_recall": round(prompt_doc_id_recall, 2),
                "prompt_doc_id_f1": round(prompt_doc_id_f1, 2),
                "cited_sources_count": len(cited_sources),
                "prompt_source_overlap_count": prompt_source_overlap_count,
                "prompt_source_precision": round(prompt_source_precision, 2),
                "prompt_source_recall": round(prompt_source_recall, 2),
                "prompt_source_f1": round(prompt_source_f1, 2),
                "confidence": round(confidence, 2),
                "latency_ms": round(latency_ms, 1),
                **_latency_stage_row_fields(merged_latency),
                "retrieval_mode": pl.get("retrieval_mode", "unknown"),
                "query_rewrite_enabled": bool(pl.get("query_rewrite_enabled", False)),
                "hybrid_retrieval_enabled": bool(pl.get("hybrid_retrieval_enabled", False)),
                "groundedness": round(groundedness, 2),
                "prompt_source_alignment": round(prompt_source_alignment, 2),
                "answer_relevance": round(answer_relevance, 2),
                "hallucination_score": round(hallucination_score, 2),
                "has_hallucination": bool(has_hallucination),
                "groundedness_score": round(judge_result.groundedness_score, 2),
                "prompt_source_alignment_score": round(judge_result.prompt_source_alignment_score, 2),
                "answer_relevance_score": round(judge_result.answer_relevance_score, 2),
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
            "avg_recall_at_k": round(float(np.mean(recall_at_k_values)), 2) if recall_at_k_values else 0.0,
            "avg_source_recall": round(float(np.mean(source_recall_values)), 2) if source_recall_values else 0.0,
            "avg_precision_at_k": round(float(np.mean(precision_at_k_values)), 2) if precision_at_k_values else 0.0,
            "mrr": round(float(np.mean(reciprocal_rank_values)), 2) if reciprocal_rank_values else 0.0,
            "map": round(float(np.mean(average_precision_values)), 2) if average_precision_values else 0.0,
            "avg_confidence": round(float(np.mean(confidence_values)), 2) if confidence_values else 0.0,
            "avg_latency_ms": round(float(np.mean(latency_values)), 1) if latency_values else 0.0,
            "doc_id_hit_rate": round(doc_id_hits / entries_with_expected_doc_ids, 2)
            if entries_with_expected_doc_ids
            else 0.0,
            "source_hit_rate": round(source_hits / entries_with_expected_sources, 2)
            if entries_with_expected_sources
            else 0.0,
            "answer_exact_match_rate": round(float(np.mean(answer_exact_match_values)), 2)
            if answer_exact_match_values
            else 0.0,
            "avg_answer_precision": round(float(np.mean(answer_precision_values)), 2)
            if answer_precision_values
            else 0.0,
            "avg_answer_recall": round(float(np.mean(answer_recall_values)), 2)
            if answer_recall_values
            else 0.0,
            "avg_answer_f1": round(float(np.mean(answer_f1_values)), 2)
            if answer_f1_values
            else 0.0,
            "avg_prompt_doc_id_precision": round(float(np.mean(prompt_doc_id_precision_values)), 2)
            if prompt_doc_id_precision_values
            else 0.0,
            "avg_prompt_doc_id_recall": round(float(np.mean(prompt_doc_id_recall_values)), 2)
            if prompt_doc_id_recall_values
            else 0.0,
            "avg_prompt_doc_id_f1": round(float(np.mean(prompt_doc_id_f1_values)), 2)
            if prompt_doc_id_f1_values
            else 0.0,
            "avg_prompt_source_precision": round(float(np.mean(prompt_source_precision_values)), 2)
            if prompt_source_precision_values
            else 0.0,
            "avg_prompt_source_recall": round(float(np.mean(prompt_source_recall_values)), 2)
            if prompt_source_recall_values
            else 0.0,
            "avg_prompt_source_f1": round(float(np.mean(prompt_source_f1_values)), 2)
            if prompt_source_f1_values
            else 0.0,
            "prompt_doc_id_hit_rate": round(prompt_doc_id_hits / entries_with_expected_doc_ids, 2)
            if entries_with_expected_doc_ids
            else 0.0,
            "prompt_source_hit_rate": round(prompt_source_hits / entries_with_expected_sources, 2)
            if entries_with_expected_sources
            else 0.0,
            "avg_groundedness": round(float(np.mean(groundedness_values)), 2)
            if groundedness_values
            else 0.0,
            "avg_prompt_source_alignment": round(float(np.mean(prompt_source_alignment_values)), 2)
            if prompt_source_alignment_values
            else 0.0,
            "avg_answer_relevance": round(float(np.mean(answer_relevance_values)), 2)
            if answer_relevance_values
            else 0.0,
            "avg_hallucination_score": round(float(np.mean(hallucination_score_values)), 2)
            if hallucination_score_values
            else 0.0,
            "hallucination_rate": round(
                sum(1 for flag in hallucination_flags if flag) / len(hallucination_flags),
                2,
            )
            if hallucination_flags
            else 0.0,
        }

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
            rebuilt.append(
                BenchmarkRow(entry_id=row.entry_id, question=row.question, data=d)
            )

        row_dicts_final = [row.to_dict() for row in rebuilt]
        mm_raw = aggregate_multimodal_metrics(row_dicts_final)
        multimodal_metrics = None
        if mm_raw and mm_raw.get("has_multimodal_assets"):
            multimodal_metrics = dict(mm_raw)

        return BenchmarkResult(
            summary=BenchmarkSummary(data=summary_payload),
            rows=rebuilt,
            correlations=correlations,
            failures=failures_report,
            multimodal_metrics=multimodal_metrics,
        )

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

    def _compute_answer_exact_match(self, *, generated_answer: str, expected_answer: str) -> float:
        return float(self._normalize_text(generated_answer) == self._normalize_text(expected_answer))

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
