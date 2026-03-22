"""Build query-log payloads from a built pipeline + latency (shared by RAG paths)."""

from __future__ import annotations

from src.domain.query_log_ingress_payload import QueryLogIngressPayload
from src.domain.pipeline_latency import PipelineLatency
from src.domain.pipeline_payloads import PipelineBuildResult
from src.domain.project import Project


def latency_fields_for_query_log(latency: PipelineLatency) -> dict[str, float]:
    d = latency.to_dict()
    return {
        "query_rewrite_ms": d["query_rewrite_ms"],
        "retrieval_ms": d["retrieval_ms"],
        "reranking_ms": d["reranking_ms"],
        "prompt_build_ms": d["prompt_build_ms"],
        "answer_generation_ms": d["answer_generation_ms"],
        "total_latency_ms": d["total_ms"],
    }


def build_query_log_ingress_payload(
    *,
    project: Project,
    question: str,
    pipeline: PipelineBuildResult,
    latency: PipelineLatency,
    answer: str | None = None,
) -> QueryLogIngressPayload:
    section_expansion = pipeline.section_expansion
    context_compression = pipeline.context_compression
    stage = latency_fields_for_query_log(latency)
    return QueryLogIngressPayload(
        question=question,
        rewritten_query=pipeline.rewritten_question,
        project_id=project.project_id,
        user_id=project.user_id,
        selected_doc_ids=tuple(pipeline.selected_doc_ids),
        retrieved_doc_ids=tuple(pipeline.recalled_doc_ids),
        latency_ms=latency.total_ms,
        confidence=pipeline.confidence,
        hybrid_retrieval_enabled=pipeline.hybrid_retrieval_enabled,
        retrieval_mode=pipeline.retrieval_mode,
        query_intent=pipeline.query_intent.value,
        table_aware_qa_enabled=pipeline.table_aware_qa_enabled,
        retrieval_strategy=pipeline.retrieval_strategy.to_dict(),
        context_compression_chars_before=context_compression.chars_before,
        context_compression_chars_after=context_compression.chars_after,
        context_compression_ratio=context_compression.ratio,
        section_expansion_count=section_expansion.section_expansion_count,
        expanded_assets_count=section_expansion.expanded_assets_count,
        query_rewrite_ms=stage["query_rewrite_ms"],
        retrieval_ms=stage["retrieval_ms"],
        reranking_ms=stage["reranking_ms"],
        prompt_build_ms=stage["prompt_build_ms"],
        answer_generation_ms=stage["answer_generation_ms"],
        total_latency_ms=stage["total_latency_ms"],
        answer=answer,
    )
