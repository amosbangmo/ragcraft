"""Shared RAG inspect + answer + latency merge for manual and gold QA evaluation flows."""

from __future__ import annotations

from time import perf_counter

from src.domain.pipeline_latency import merge_with_answer_stage
from src.domain.project import Project
from src.infrastructure.adapters.rag.rag_service import RAGService


def run_rag_inspect_and_answer_for_eval(
    *,
    rag_service: RAGService,
    project: Project,
    question: str,
    enable_query_rewrite: bool | None,
    enable_hybrid_retrieval: bool | None,
) -> dict:
    started = perf_counter()
    pipeline = rag_service.inspect_pipeline(
        project,
        question,
        [],
        enable_query_rewrite_override=enable_query_rewrite,
        enable_hybrid_retrieval_override=enable_hybrid_retrieval,
    )
    answer = ""
    answer_generation_ms = 0.0
    if pipeline is not None:
        gen_started = perf_counter()
        answer = rag_service.generate_answer_from_pipeline(project=project, pipeline=pipeline)
        answer_generation_ms = (perf_counter() - gen_started) * 1000.0
    latency_ms = (perf_counter() - started) * 1000.0
    latency_dict = None
    if pipeline is not None:
        full_latency = merge_with_answer_stage(
            pipeline.latency,
            answer_generation_ms=answer_generation_ms,
            total_ms=latency_ms,
        )
        latency_dict = full_latency.to_dict()
        pipeline.latency = latency_dict
        pipeline.latency_ms = latency_ms

    return {
        "pipeline": pipeline,
        "answer": answer,
        "latency_ms": latency_ms,
        "latency": latency_dict,
    }
