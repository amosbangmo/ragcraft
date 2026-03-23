"""Pure retrieval-mode comparison workflow (no LLM answer). Invoked from the application use case."""

from __future__ import annotations

from collections.abc import Callable
from time import perf_counter
from typing import Any

from domain.projects.project import Project
from domain.rag.pipeline_payloads import PipelineBuildResult

InspectPipelineFn = Callable[..., PipelineBuildResult | None]


def compare_retrieval_modes_for_project(
    *,
    inspect_pipeline: InspectPipelineFn,
    project: Project,
    questions: list[str],
    enable_query_rewrite: bool,
) -> dict[str, Any]:
    normalized_questions = [q.strip() for q in questions if q and q.strip()]
    rows: list[dict] = []

    for question in normalized_questions:
        faiss_pipeline, faiss_latency_ms = _run_pipeline(
            inspect_pipeline=inspect_pipeline,
            project=project,
            question=question,
            enable_query_rewrite=enable_query_rewrite,
            enable_hybrid_retrieval=False,
        )
        hybrid_pipeline, hybrid_latency_ms = _run_pipeline(
            inspect_pipeline=inspect_pipeline,
            project=project,
            question=question,
            enable_query_rewrite=enable_query_rewrite,
            enable_hybrid_retrieval=True,
        )

        faiss_doc_ids = _extract_doc_ids(faiss_pipeline)
        hybrid_doc_ids = _extract_doc_ids(hybrid_pipeline)

        shared_doc_ids = sorted(set(faiss_doc_ids).intersection(hybrid_doc_ids))
        hybrid_only_doc_ids = sorted(set(hybrid_doc_ids) - set(faiss_doc_ids))

        row = {
            "question": question,
            "rewritten_query": _get_rewritten_query(faiss_pipeline, hybrid_pipeline),
            "faiss_recall_docs": len(_safe_get(faiss_pipeline, "recalled_summary_docs", [])),
            "hybrid_recall_docs": len(_safe_get(hybrid_pipeline, "recalled_summary_docs", [])),
            "faiss_recall_doc_ids": len(faiss_doc_ids),
            "hybrid_recall_doc_ids": len(hybrid_doc_ids),
            "faiss_prompt_assets": len(_safe_get(faiss_pipeline, "reranked_raw_assets", [])),
            "hybrid_prompt_assets": len(_safe_get(hybrid_pipeline, "reranked_raw_assets", [])),
            "faiss_confidence": float(_safe_get(faiss_pipeline, "confidence", 0.0)),
            "hybrid_confidence": float(_safe_get(hybrid_pipeline, "confidence", 0.0)),
            "faiss_latency_ms": round(faiss_latency_ms, 1),
            "hybrid_latency_ms": round(hybrid_latency_ms, 1),
            "shared_doc_ids": len(shared_doc_ids),
            "hybrid_only_doc_ids": len(hybrid_only_doc_ids),
            "faiss_selected_doc_ids": len(_safe_get(faiss_pipeline, "selected_doc_ids", [])),
            "hybrid_selected_doc_ids": len(_safe_get(hybrid_pipeline, "selected_doc_ids", [])),
            "faiss_has_pipeline": faiss_pipeline is not None,
            "hybrid_has_pipeline": hybrid_pipeline is not None,
        }
        rows.append(row)

    summary = _build_summary(rows, enable_query_rewrite=enable_query_rewrite)

    return {
        "questions": normalized_questions,
        "summary": summary,
        "rows": rows,
    }


def _run_pipeline(
    *,
    inspect_pipeline: InspectPipelineFn,
    project: Project,
    question: str,
    enable_query_rewrite: bool,
    enable_hybrid_retrieval: bool,
) -> tuple[PipelineBuildResult | None, float]:
    started = perf_counter()
    pipeline = inspect_pipeline(
        project,
        question,
        [],
        enable_query_rewrite_override=enable_query_rewrite,
        enable_hybrid_retrieval_override=enable_hybrid_retrieval,
    )
    elapsed_ms = (perf_counter() - started) * 1000.0
    if pipeline is not None:
        instrumented = pipeline.latency_ms
        if instrumented is not None:
            try:
                return pipeline, float(instrumented)
            except (TypeError, ValueError):
                pass
    return pipeline, elapsed_ms


def _extract_doc_ids(pipeline: PipelineBuildResult | None) -> list[str]:
    if pipeline is None:
        return []
    return list(pipeline.recalled_doc_ids)


def _get_rewritten_query(
    faiss_pipeline: PipelineBuildResult | None,
    hybrid_pipeline: PipelineBuildResult | None,
) -> str:
    if faiss_pipeline is not None:
        return str(faiss_pipeline.rewritten_question)
    if hybrid_pipeline is not None:
        return str(hybrid_pipeline.rewritten_question)
    return ""


def _safe_get(payload: PipelineBuildResult | None, key: str, default: Any) -> Any:
    if payload is None:
        return default
    return getattr(payload, key, default)


def _build_summary(rows: list[dict], *, enable_query_rewrite: bool) -> dict:
    if not rows:
        return {
            "total_questions": 0,
            "query_rewrite_enabled": enable_query_rewrite,
            "avg_faiss_recall_doc_ids": 0.0,
            "avg_hybrid_recall_doc_ids": 0.0,
            "avg_faiss_prompt_assets": 0.0,
            "avg_hybrid_prompt_assets": 0.0,
            "avg_faiss_confidence": 0.0,
            "avg_hybrid_confidence": 0.0,
            "avg_faiss_latency_ms": 0.0,
            "avg_hybrid_latency_ms": 0.0,
            "hybrid_wins_on_recall_doc_ids": 0,
            "hybrid_wins_on_confidence": 0,
            "hybrid_wins_on_prompt_assets": 0,
        }

    total = len(rows)

    def avg(key: str) -> float:
        return round(sum(float(row[key]) for row in rows) / total, 2)

    hybrid_wins_on_recall_doc_ids = sum(
        1 for row in rows if row["hybrid_recall_doc_ids"] > row["faiss_recall_doc_ids"]
    )
    hybrid_wins_on_confidence = sum(
        1 for row in rows if row["hybrid_confidence"] > row["faiss_confidence"]
    )
    hybrid_wins_on_prompt_assets = sum(
        1 for row in rows if row["hybrid_prompt_assets"] > row["faiss_prompt_assets"]
    )

    return {
        "total_questions": total,
        "query_rewrite_enabled": enable_query_rewrite,
        "avg_faiss_recall_doc_ids": avg("faiss_recall_doc_ids"),
        "avg_hybrid_recall_doc_ids": avg("hybrid_recall_doc_ids"),
        "avg_faiss_prompt_assets": avg("faiss_prompt_assets"),
        "avg_hybrid_prompt_assets": avg("hybrid_prompt_assets"),
        "avg_faiss_confidence": avg("faiss_confidence"),
        "avg_hybrid_confidence": avg("hybrid_confidence"),
        "avg_faiss_latency_ms": avg("faiss_latency_ms"),
        "avg_hybrid_latency_ms": avg("hybrid_latency_ms"),
        "hybrid_wins_on_recall_doc_ids": hybrid_wins_on_recall_doc_ids,
        "hybrid_wins_on_confidence": hybrid_wins_on_confidence,
        "hybrid_wins_on_prompt_assets": hybrid_wins_on_prompt_assets,
    }
