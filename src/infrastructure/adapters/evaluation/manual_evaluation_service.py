from __future__ import annotations

from time import perf_counter
from typing import TYPE_CHECKING, Any

from src.domain.pipeline_latency import merge_with_answer_stage
from src.domain.pipeline_payloads import PipelineBuildResult
from src.domain.manual_evaluation_result import (
    ManualEvaluationAnswerCitationQuality,
    ManualEvaluationAnswerQuality,
    ManualEvaluationExpectationComparison,
    ManualEvaluationPipelineSignals,
    ManualEvaluationPromptSourceQuality,
    ManualEvaluationResult,
    ManualEvaluationRetrievalQuality,
)
from src.domain.qa_dataset_entry import QADatasetEntry
from src.domain.rag_inspect_answer_run import RagInspectAnswerRun
from src.domain.ports.gold_qa_benchmark_port import GoldQaBenchmarkPort
from src.infrastructure.adapters.evaluation.llm_judge_service import JUDGE_FAILURE_REASON

if TYPE_CHECKING:
    from src.frontend_gateway.protocol import BackendClient

_MANUAL_EVAL_ENTRY_ID = 0

# Thresholds for automatic issue detection (tune here).
_GROUNDEDNESS_LOW = 0.5
_ANSWER_RELEVANCE_LOW = 0.5
_HALLUCINATION_SCORE_LOW = 0.5
_PROMPT_DOC_ID_RECALL_LOW = 0.5
_CITATION_DOC_ID_RECALL_LOW = 0.5
_RECALL_AT_K_LOW = 0.5
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
    recall_at_k: float | None,
    source_recall: float | None,
    prompt_doc_id_recall: float | None,
    citation_doc_id_recall: float | None,
    expected_doc_ids: list[str],
    expected_sources: list[str],
    expected_answer: str | None,
    pipeline_failed: bool = False,
) -> list[str]:
    issues: list[str] = []

    if (not has_pipeline or not answer_stripped) and not pipeline_failed:
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

    if expected_doc_ids and recall_at_k is not None and recall_at_k < _RECALL_AT_K_LOW:
        issues.append("No expected document retrieved")

    if expected_sources:
        if source_recall is not None and source_recall < _SOURCE_RECALL_LOW:
            issues.append("No expected source retrieved")

    if expected_doc_ids:
        if prompt_doc_id_recall is not None and prompt_doc_id_recall < _PROMPT_DOC_ID_RECALL_LOW:
            issues.append("Low prompt doc ID recall")
        if (
            citation_doc_id_recall is not None
            and citation_doc_id_recall < _CITATION_DOC_ID_RECALL_LOW
        ):
            issues.append("Low answer citation recall (expected doc IDs)")

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


def _row_optional_float(row: dict[str, Any], key: str) -> float | None:
    v = row.get(key)
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _row_optional_int(row: dict[str, Any], key: str) -> int | None:
    v = row.get(key)
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


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


def manual_evaluation_result_from_eval_row(
    *,
    row: dict[str, Any],
    q: str,
    exp_ans: str | None,
    exp_docs: list[str],
    exp_src: list[str],
    pipeline: PipelineBuildResult | None,
    answer: str,
    latency_ms: float,
    full_latency_dict: dict[str, float] | None,
) -> ManualEvaluationResult:
    has_pipeline = pipeline is not None
    judge_failed = bool(row.get("judge_failed"))
    pipeline_failed = bool(row.get("pipeline_failed"))
    judge_metrics_ok = has_pipeline and not judge_failed

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

    conf_raw = row.get("confidence")
    confidence = float(conf_raw) if conf_raw is not None else 0.0

    groundedness = _row_optional_float(row, "groundedness_score") if judge_metrics_ok else None
    answer_relevance = _row_optional_float(row, "answer_relevance_score") if judge_metrics_ok else None
    hallucination_score = _row_optional_float(row, "hallucination_score") if judge_metrics_ok else None
    hallu_raw = row.get("has_hallucination")
    has_hallucination = (
        None
        if not judge_metrics_ok
        else (None if hallu_raw is None else bool(hallu_raw))
    )
    citation_faith = _row_optional_float(row, "citation_faithfulness_score") if judge_metrics_ok else None

    recall_at_k_v = _row_optional_float(row, "recall_at_k") if exp_docs else None
    source_recall_v = _row_optional_float(row, "source_recall") if exp_src else None
    precision_at_k_v = _row_optional_float(row, "precision_at_k") if exp_docs else None
    reciprocal_rank_v = _row_optional_float(row, "reciprocal_rank") if exp_docs else None
    average_precision_v = _row_optional_float(row, "average_precision") if exp_docs else None

    prompt_doc_p = _row_optional_float(row, "prompt_doc_id_precision") if exp_docs else None
    prompt_doc_r = _row_optional_float(row, "prompt_doc_id_recall") if exp_docs else None
    prompt_doc_f1 = _row_optional_float(row, "prompt_doc_id_f1") if exp_docs else None

    citation_doc_p = _row_optional_float(row, "citation_doc_id_precision") if has_pipeline else None
    citation_doc_r = _row_optional_float(row, "citation_doc_id_recall") if has_pipeline else None
    citation_doc_f1 = _row_optional_float(row, "citation_doc_id_f1") if has_pipeline else None
    citation_overlap = _row_optional_int(row, "citation_doc_id_overlap_count")
    citation_ids_n = _row_optional_int(row, "citation_doc_ids_count")

    answer_f1 = _row_optional_float(row, "answer_f1") if exp_ans else None
    answer_correctness = (
        _row_optional_float(row, "answer_correctness_score")
        if judge_metrics_ok and exp_ans
        else None
    )
    semantic_sim = _row_optional_float(row, "semantic_similarity") if exp_ans else None
    ndcg_v = _row_optional_float(row, "ndcg_at_k") if exp_docs else None

    answer_stripped = (answer or "").strip()

    answer_quality = ManualEvaluationAnswerQuality(
        confidence=confidence,
        groundedness_score=groundedness,
        citation_faithfulness_score=citation_faith,
        answer_relevance_score=answer_relevance,
        hallucination_score=hallucination_score,
        has_hallucination=has_hallucination,
        answer_f1=answer_f1,
        answer_correctness_score=answer_correctness,
        semantic_similarity=semantic_sim,
    )

    answer_citation_quality = (
        ManualEvaluationAnswerCitationQuality(
            citation_doc_id_precision=citation_doc_p,
            citation_doc_id_recall=citation_doc_r,
            citation_doc_id_f1=citation_doc_f1,
            citation_doc_id_overlap_count=citation_overlap,
            citation_doc_ids_count=citation_ids_n,
        )
        if has_pipeline
        else None
    )

    prompt_source_quality = ManualEvaluationPromptSourceQuality(
        prompt_doc_id_precision=prompt_doc_p,
        prompt_doc_id_recall=prompt_doc_r,
        prompt_doc_id_f1=prompt_doc_f1,
    )

    rdoc_n = _row_optional_int(row, "retrieved_doc_ids_count")
    rsrc_n = _row_optional_int(row, "retrieved_sources_count")
    retrieval_quality = ManualEvaluationRetrievalQuality(
        recall_at_k=recall_at_k_v,
        source_recall=source_recall_v,
        precision_at_k=precision_at_k_v,
        reciprocal_rank=reciprocal_rank_v,
        average_precision=average_precision_v,
        retrieved_doc_ids_count=int(rdoc_n if rdoc_n is not None else 0),
        selected_source_count=int(rsrc_n if rsrc_n is not None else 0),
        ndcg_at_k=ndcg_v,
    )

    pipeline_signals = ManualEvaluationPipelineSignals(
        confidence=confidence,
        retrieval_mode=str(row.get("retrieval_mode", "none")),
        query_rewrite_enabled=bool(row.get("query_rewrite_enabled", False)),
        hybrid_retrieval_enabled=bool(row.get("hybrid_retrieval_enabled", False)),
        latency_ms=float(row.get("latency_ms", round(latency_ms, 1))),
        stage_latency=full_latency_dict,
    )

    jfr_raw = row.get("judge_failure_reason")
    judge_failure_reason = (
        jfr_raw.strip()
        if isinstance(jfr_raw, str) and jfr_raw.strip()
        else None
    )

    head_issues: list[str] = []
    if pipeline_failed:
        head_issues.append("Retrieval pipeline did not complete for this question.")
    elif judge_failed:
        if judge_failure_reason and judge_failure_reason != JUDGE_FAILURE_REASON:
            head_issues.append(
                f"LLM judge could not score this answer ({judge_failure_reason})."
            )
        else:
            head_issues.append("LLM judge could not score this answer.")

    tail = detect_manual_evaluation_issues(
        answer_stripped=answer_stripped,
        has_pipeline=has_pipeline,
        confidence=confidence,
        groundedness=groundedness,
        answer_relevance=answer_relevance,
        hallucination_score=hallucination_score,
        has_hallucination=has_hallucination,
        recall_at_k=recall_at_k_v,
        source_recall=source_recall_v,
        prompt_doc_id_recall=prompt_doc_r,
        citation_doc_id_recall=citation_doc_r,
        expected_doc_ids=exp_docs,
        expected_sources=exp_src,
        expected_answer=exp_ans,
        pipeline_failed=pipeline_failed,
    )
    seen_i: set[str] = set()
    issues: list[str] = []
    for item in head_issues + tail:
        if item not in seen_i:
            seen_i.add(item)
            issues.append(item)

    return ManualEvaluationResult(
        question=q,
        answer=answer or "",
        expected_answer=exp_ans,
        confidence=confidence,
        pipeline_failed=pipeline_failed,
        judge_failed=judge_failed,
        judge_failure_reason=judge_failure_reason,
        prompt_sources=prompt_sources,
        raw_assets=raw_assets,
        answer_quality=answer_quality,
        answer_citation_quality=answer_citation_quality,
        prompt_source_quality=prompt_source_quality,
        retrieval_quality=retrieval_quality,
        pipeline_signals=pipeline_signals,
        expectation_comparison=comparison,
        detected_issues=issues,
    )


def manual_evaluation_result_from_rag_outputs(
    *,
    user_id: str,
    project_id: str,
    q: str,
    exp_ans: str | None,
    exp_docs: list[str],
    exp_src: list[str],
    pipeline: PipelineBuildResult | None,
    answer: str,
    latency_ms: float,
    full_latency_dict: dict[str, float] | None,
    gold_qa_benchmark: GoldQaBenchmarkPort,
) -> ManualEvaluationResult:
    entry = QADatasetEntry(
        id=_MANUAL_EVAL_ENTRY_ID,
        user_id=user_id,
        project_id=project_id,
        question=q,
        expected_answer=exp_ans,
        expected_doc_ids=exp_docs,
        expected_sources=exp_src,
    )

    run = RagInspectAnswerRun(
        pipeline=pipeline,
        answer=answer,
        latency_ms=latency_ms,
        full_latency=full_latency_dict,
    )

    def pipeline_runner(_e: QADatasetEntry) -> RagInspectAnswerRun:
        return run

    benchmark = gold_qa_benchmark.evaluate_gold_qa_dataset(
        entries=[entry],
        pipeline_runner=pipeline_runner,
    )
    return manual_evaluation_result_from_eval_row(
        row=benchmark.rows[0].data,
        q=q,
        exp_ans=exp_ans,
        exp_docs=exp_docs,
        exp_src=exp_src,
        pipeline=pipeline,
        answer=answer,
        latency_ms=latency_ms,
        full_latency_dict=full_latency_dict,
    )


class ManualEvaluationService:
    @staticmethod
    def evaluate_question(
        *,
        backend_client: BackendClient,
        user_id: str,
        project_id: str,
        question: str,
        expected_answer: str | None = None,
        expected_doc_ids: list[str] | None = None,
        expected_sources: list[str] | None = None,
    ) -> ManualEvaluationResult:
        """Prefer :class:`~src.application.use_cases.evaluation.run_manual_evaluation.RunManualEvaluationUseCase` for new wiring; kept for tests and ``BackendClient``-based call sites."""
        q = (question or "").strip()
        exp_ans = (expected_answer or "").strip() or None
        exp_docs = list(expected_doc_ids or [])
        exp_src = list(expected_sources or [])

        project = backend_client.get_project(user_id, project_id)

        started = perf_counter()
        pipeline = backend_client.inspect_retrieval(
            user_id=user_id,
            project_id=project_id,
            question=q,
            chat_history=[],
        )
        answer = ""
        answer_generation_ms = 0.0
        if pipeline is not None:
            gen_started = perf_counter()
            answer = backend_client.generate_answer_from_pipeline(
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

        run = RagInspectAnswerRun(
            pipeline=pipeline,
            answer=answer,
            latency_ms=latency_ms,
            full_latency=full_latency_dict,
        )

        def pipeline_runner(_e: QADatasetEntry) -> RagInspectAnswerRun:
            return run

        benchmark = backend_client.evaluate_gold_qa_dataset_with_runner(
            entries=[entry],
            pipeline_runner=pipeline_runner,
        )
        return manual_evaluation_result_from_eval_row(
            row=benchmark.rows[0].data,
            q=q,
            exp_ans=exp_ans,
            exp_docs=exp_docs,
            exp_src=exp_src,
            pipeline=pipeline,
            answer=answer,
            latency_ms=latency_ms,
            full_latency_dict=full_latency_dict,
        )
