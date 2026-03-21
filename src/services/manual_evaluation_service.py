from __future__ import annotations

from time import perf_counter
from typing import TYPE_CHECKING, Any

from src.domain.pipeline_latency import merge_with_answer_stage
from src.domain.pipeline_payloads import PipelineBuildResult
from src.domain.manual_evaluation_result import (
    ManualEvaluationAnswerQuality,
    ManualEvaluationCitationQuality,
    ManualEvaluationExpectationComparison,
    ManualEvaluationPipelineSignals,
    ManualEvaluationResult,
    ManualEvaluationRetrievalQuality,
)
from src.domain.qa_dataset_entry import QADatasetEntry

if TYPE_CHECKING:
    from src.app.ragcraft_app import RAGCraftApp

_MANUAL_EVAL_ENTRY_ID = 0

# Thresholds for automatic issue detection (tune here).
_GROUNDEDNESS_LOW = 0.5
_ANSWER_RELEVANCE_LOW = 0.5
_HALLUCINATION_SCORE_LOW = 0.5
_CITATION_SOURCE_RECALL_LOW = 0.5
_DOC_ID_RECALL_LOW = 0.5
_SOURCE_RECALL_LOW = 0.5
_CONFIDENCE_LOW = 0.45


def build_expectation_comparison(
    *,
    expected_doc_ids: list[str],
    expected_sources: list[str],
    retrieved_doc_ids: list[str],
    retrieved_sources: list[str],
) -> ManualEvaluationExpectationComparison:
    exp_docs = list(expected_doc_ids)
    exp_src = list(expected_sources)
    ret_docs = list(retrieved_doc_ids)
    ret_src = list(retrieved_sources)

    exp_doc_set = set(exp_docs)
    ret_doc_set = set(ret_docs)
    exp_src_set = set(exp_src)
    ret_src_set = set(ret_src)

    matched_doc_ids = sorted(exp_doc_set & ret_doc_set)
    missing_doc_ids = sorted(exp_doc_set - ret_doc_set)
    matched_sources = sorted(exp_src_set & ret_src_set)
    missing_sources = sorted(exp_src_set - ret_src_set)

    return ManualEvaluationExpectationComparison(
        expected_doc_ids=exp_docs,
        retrieved_doc_ids=ret_docs,
        matched_doc_ids=matched_doc_ids,
        missing_doc_ids=missing_doc_ids,
        expected_sources=exp_src,
        retrieved_sources=ret_src,
        matched_sources=matched_sources,
        missing_sources=missing_sources,
    )


def detect_manual_evaluation_issues(
    *,
    answer_stripped: str,
    has_pipeline: bool,
    confidence: float,
    groundedness: float | None,
    answer_relevance: float | None,
    hallucination_score: float | None,
    has_hallucination: bool | None,
    doc_id_recall: float | None,
    source_recall: float | None,
    citation_source_recall: float | None,
    expected_doc_ids: list[str],
    expected_sources: list[str],
    expected_answer: str | None,
) -> list[str]:
    issues: list[str] = []

    if not has_pipeline or not answer_stripped:
        issues.append("No answer generated")

    if confidence < _CONFIDENCE_LOW:
        issues.append("Low confidence")

    if groundedness is not None and groundedness < _GROUNDEDNESS_LOW:
        issues.append("Low groundedness")

    if answer_relevance is not None and answer_relevance < _ANSWER_RELEVANCE_LOW:
        issues.append("Low answer relevance")

    if has_hallucination is True:
        issues.append("Hallucination detected")
    elif hallucination_score is not None and hallucination_score < _HALLUCINATION_SCORE_LOW:
        issues.append("Hallucination detected")

    if expected_doc_ids and doc_id_recall is not None and doc_id_recall < _DOC_ID_RECALL_LOW:
        issues.append("No expected document retrieved")

    if expected_sources:
        if source_recall is not None and source_recall < _SOURCE_RECALL_LOW:
            issues.append("No expected source retrieved")
        if citation_source_recall is not None and citation_source_recall < _CITATION_SOURCE_RECALL_LOW:
            issues.append("Low citation recall")

    if expected_answer and not answer_stripped:
        issues.append("Missing answer vs expected reference")

    # De-duplicate while preserving order
    seen: set[str] = set()
    ordered: list[str] = []
    for item in issues:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def _ordered_sources_from_pipeline(
    pipeline: PipelineBuildResult | dict[str, Any] | None,
) -> list[str]:
    if not pipeline:
        return []
    refs = (
        pipeline.prompt_sources
        if isinstance(pipeline, PipelineBuildResult)
        else (pipeline.get("prompt_sources") or [])
    )
    if not isinstance(refs, list):
        return []
    ordered: list[str] = []
    seen: set[str] = set()
    for ref in refs:
        if not isinstance(ref, dict):
            continue
        sf = ref.get("source_file")
        if sf and sf not in seen:
            seen.add(sf)
            ordered.append(str(sf))
    return ordered


class ManualEvaluationService:
    @staticmethod
    def evaluate_question(
        *,
        app: RAGCraftApp,
        user_id: str,
        project_id: str,
        question: str,
        expected_answer: str | None = None,
        expected_doc_ids: list[str] | None = None,
        expected_sources: list[str] | None = None,
    ) -> ManualEvaluationResult:
        q = (question or "").strip()
        exp_ans = (expected_answer or "").strip() or None
        exp_docs = list(expected_doc_ids or [])
        exp_src = list(expected_sources or [])

        project = app.get_project(user_id, project_id)

        started = perf_counter()
        pipeline = app.inspect_retrieval(
            user_id=user_id,
            project_id=project_id,
            question=q,
            chat_history=[],
        )
        answer = ""
        answer_generation_ms = 0.0
        if pipeline is not None:
            gen_started = perf_counter()
            answer = app.rag_service.generate_answer_from_pipeline(
                project=project,
                pipeline=pipeline,
            )
            answer_generation_ms = (perf_counter() - gen_started) * 1000.0
        latency_ms = (perf_counter() - started) * 1000.0

        full_latency_dict: dict[str, float] | None = None
        if pipeline is not None:
            full_lat = merge_with_answer_stage(
                pipeline.latency,
                answer_generation_ms=answer_generation_ms,
                total_ms=latency_ms,
            )
            full_latency_dict = full_lat.to_dict()
            pipeline.latency = full_latency_dict
            pipeline.latency_ms = latency_ms

        entry = QADatasetEntry(
            id=_MANUAL_EVAL_ENTRY_ID,
            user_id=user_id,
            project_id=project_id,
            question=q,
            expected_answer=exp_ans,
            expected_doc_ids=exp_docs,
            expected_sources=exp_src,
        )

        def pipeline_runner(_e: QADatasetEntry) -> dict[str, Any]:
            return {
                "pipeline": pipeline,
                "answer": answer,
                "latency_ms": latency_ms,
                "latency": full_latency_dict,
            }

        benchmark = app.evaluation_service.evaluate_gold_qa_dataset(
            entries=[entry],
            pipeline_runner=pipeline_runner,
        )
        row = benchmark.rows[0].data

        prompt_sources: list[dict[str, Any]] = []
        raw_assets: list[dict[str, Any]] = []
        if pipeline is not None:
            prompt_sources = [r for r in pipeline.prompt_sources if isinstance(r, dict)]
            raw_assets = [a for a in pipeline.reranked_raw_assets if isinstance(a, dict)]

        ranked_doc_ids = [
            doc_id for doc_id in (pipeline.selected_doc_ids if pipeline else []) if doc_id
        ]
        retrieved_sources = _ordered_sources_from_pipeline(pipeline)

        comparison: ManualEvaluationExpectationComparison | None = None
        if exp_docs or exp_src:
            comparison = build_expectation_comparison(
                expected_doc_ids=exp_docs,
                expected_sources=exp_src,
                retrieved_doc_ids=ranked_doc_ids,
                retrieved_sources=retrieved_sources,
            )

        confidence = float(row.get("confidence", 0.0))
        groundedness = float(row.get("groundedness_score", row.get("groundedness", 0.0)))
        answer_relevance = float(row.get("answer_relevance_score", row.get("answer_relevance", 0.0)))
        hallucination_score = float(row.get("hallucination_score", 0.0))
        has_hallucination = bool(row.get("has_hallucination", False))
        citation_faithfulness = float(
            row.get("citation_faithfulness_score", row.get("citation_faithfulness", 0.0))
        )

        doc_id_recall_v = float(row.get("doc_id_recall", 0.0)) if exp_docs else None
        source_recall_v = float(row.get("source_recall", 0.0)) if exp_src else None
        precision_at_k_v = float(row.get("precision_at_k", 0.0)) if exp_docs else None
        reciprocal_rank_v = float(row.get("reciprocal_rank", 0.0)) if exp_docs else None
        average_precision_v = float(row.get("average_precision", 0.0)) if exp_docs else None

        citation_doc_p = float(row.get("citation_doc_id_precision", 0.0)) if exp_docs else None
        citation_doc_r = float(row.get("citation_doc_id_recall", 0.0)) if exp_docs else None
        citation_doc_f1 = float(row.get("citation_doc_id_f1", 0.0)) if exp_docs else None

        citation_src_p = float(row.get("citation_source_precision", 0.0)) if exp_src else None
        citation_src_r = float(row.get("citation_source_recall", 0.0)) if exp_src else None
        citation_src_f1 = float(row.get("citation_source_f1", 0.0)) if exp_src else None

        answer_em = float(row.get("answer_exact_match", 0.0)) if exp_ans else None
        answer_p = float(row.get("answer_precision", 0.0)) if exp_ans else None
        answer_r = float(row.get("answer_recall", 0.0)) if exp_ans else None
        answer_f1 = float(row.get("answer_f1", 0.0)) if exp_ans else None

        answer_stripped = (answer or "").strip()
        has_pipeline = pipeline is not None

        answer_quality = ManualEvaluationAnswerQuality(
            confidence=confidence,
            groundedness_score=groundedness if has_pipeline else None,
            answer_relevance_score=answer_relevance if has_pipeline else None,
            hallucination_score=hallucination_score if has_pipeline else None,
            has_hallucination=has_hallucination if has_pipeline else None,
            answer_exact_match=answer_em,
            answer_precision=answer_p,
            answer_recall=answer_r,
            answer_f1=answer_f1,
        )

        citation_quality = ManualEvaluationCitationQuality(
            citation_doc_id_precision=citation_doc_p,
            citation_doc_id_recall=citation_doc_r,
            citation_doc_id_f1=citation_doc_f1,
            citation_source_precision=citation_src_p,
            citation_source_recall=citation_src_r,
            citation_source_f1=citation_src_f1,
            citation_faithfulness_score=citation_faithfulness if has_pipeline else None,
        )

        retrieval_quality = ManualEvaluationRetrievalQuality(
            doc_id_recall=doc_id_recall_v,
            source_recall=source_recall_v,
            precision_at_k=precision_at_k_v,
            reciprocal_rank=reciprocal_rank_v,
            average_precision=average_precision_v,
            retrieved_doc_ids_count=int(row.get("retrieved_doc_ids_count", 0)),
            selected_source_count=int(row.get("retrieved_sources_count", 0)),
        )

        pipeline_signals = ManualEvaluationPipelineSignals(
            confidence=confidence,
            retrieval_mode=str(row.get("retrieval_mode", "none")),
            query_rewrite_enabled=bool(row.get("query_rewrite_enabled", False)),
            hybrid_retrieval_enabled=bool(row.get("hybrid_retrieval_enabled", False)),
            latency_ms=float(row.get("latency_ms", round(latency_ms, 1))),
            stage_latency=full_latency_dict,
        )

        issues = detect_manual_evaluation_issues(
            answer_stripped=answer_stripped,
            has_pipeline=has_pipeline,
            confidence=confidence,
            groundedness=groundedness if has_pipeline else None,
            answer_relevance=answer_relevance if has_pipeline else None,
            hallucination_score=hallucination_score if has_pipeline else None,
            has_hallucination=has_hallucination if has_pipeline else None,
            doc_id_recall=doc_id_recall_v,
            source_recall=source_recall_v,
            citation_source_recall=citation_src_r,
            expected_doc_ids=exp_docs,
            expected_sources=exp_src,
            expected_answer=exp_ans,
        )

        return ManualEvaluationResult(
            question=q,
            answer=answer or "",
            expected_answer=exp_ans,
            confidence=confidence,
            prompt_sources=prompt_sources,
            raw_assets=raw_assets,
            answer_quality=answer_quality,
            citation_quality=citation_quality,
            retrieval_quality=retrieval_quality,
            pipeline_signals=pipeline_signals,
            expectation_comparison=comparison,
            detected_issues=issues,
        )
