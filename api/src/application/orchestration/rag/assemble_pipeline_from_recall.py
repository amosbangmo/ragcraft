"""
Post–summary-recall pipeline assembly: **application-owned orchestration**.

Delegates each phase to :mod:`~application.use_cases.chat.orchestration.post_recall_pipeline_steps`
and ports on
:class:`~application.use_cases.chat.orchestration.ports.PostRecallStagePorts`.
"""

from __future__ import annotations

from time import perf_counter

from application.orchestration.rag.post_recall_pipeline_steps import (
    step_confidence,
    step_contextual_compression,
    step_docstore_hydration,
    step_prompt_assembly,
    step_rerank_and_select_summaries,
    step_section_expansion,
)
from application.orchestration.rag.ports import PostRecallStagePorts
from domain.rag.pipeline_latency import PipelineLatency
from domain.rag.pipeline_payloads import PipelineBuildResult, SummaryRecallResult
from domain.projects.project import Project


def assemble_pipeline_from_recall(
    *,
    project: Project,
    question: str,
    chat_history: list[str],
    recall: SummaryRecallResult,
    pipeline_started_monotonic: float,
    stages: PostRecallStagePorts,
) -> PipelineBuildResult | None:
    settings = recall.settings
    query_rewrite_ms = recall.query_rewrite_ms
    query_intent = recall.query_intent
    table_aware_qa_enabled = recall.table_aware_qa_enabled
    use_adaptive_retrieval = recall.use_adaptive_retrieval
    strategy = recall.strategy
    enable_hybrid_retrieval = recall.enable_hybrid_retrieval
    filters_for_retrieval = recall.filters_for_retrieval
    retrieval_ms = recall.retrieval_ms
    rewritten_question = recall.rewritten_question
    enable_query_rewrite = recall.enable_query_rewrite
    vector_summary_docs = recall.vector_summary_docs
    bm25_summary_docs = recall.bm25_summary_docs
    recalled_summary_docs = recall.recalled_summary_docs

    hydrated = step_docstore_hydration(project=project, recall=recall, stages=stages)
    if hydrated is None:
        return None

    expansion = step_section_expansion(
        project=project,
        settings=settings,
        recalled_raw_assets=hydrated.recalled_raw_assets,
        stages=stages,
    )

    reranked = step_rerank_and_select_summaries(
        recall=recall,
        pre_rerank_raw_assets=expansion.pre_rerank_raw_assets,
        stages=stages,
    )
    if reranked is None:
        return None

    compressed = step_contextual_compression(
        recall=recall,
        reranked_raw_assets=reranked.reranked_raw_assets,
        stages=stages,
    )

    prompt_out = step_prompt_assembly(
        question=question,
        chat_history=chat_history,
        recall=recall,
        prompt_context_assets=compressed.prompt_context_assets,
        stages=stages,
    )

    confidence = step_confidence(
        reranked_raw_assets=reranked.reranked_raw_assets,
        stages=stages,
    )

    retrieval_mode = "faiss+bm25" if enable_hybrid_retrieval else "faiss"
    total_pipeline_ms = (perf_counter() - pipeline_started_monotonic) * 1000.0
    latency = PipelineLatency(
        query_rewrite_ms=query_rewrite_ms,
        retrieval_ms=retrieval_ms,
        reranking_ms=reranked.reranking_ms,
        prompt_build_ms=prompt_out.prompt_build_ms,
        answer_generation_ms=0.0,
        total_ms=total_pipeline_ms,
    )
    return PipelineBuildResult(
        question=question,
        rewritten_question=rewritten_question,
        query_intent=query_intent,
        table_aware_qa_enabled=table_aware_qa_enabled,
        chat_history=list(chat_history),
        retrieval_mode=retrieval_mode,
        query_rewrite_enabled=enable_query_rewrite,
        hybrid_retrieval_enabled=enable_hybrid_retrieval,
        adaptive_retrieval_enabled=use_adaptive_retrieval,
        retrieval_strategy=strategy,
        retrieval_filters=(
            filters_for_retrieval.to_dict()
            if filters_for_retrieval is not None
            else None
        ),
        vector_summary_docs=vector_summary_docs,
        bm25_summary_docs=bm25_summary_docs,
        recalled_summary_docs=recalled_summary_docs,
        recalled_doc_ids=hydrated.recalled_doc_ids,
        recalled_raw_assets=hydrated.recalled_raw_assets,
        pre_rerank_raw_assets=expansion.pre_rerank_raw_assets,
        section_expansion=expansion.section_expansion,
        selected_summary_docs=reranked.selected_summary_docs,
        selected_doc_ids=reranked.selected_doc_ids,
        reranked_raw_assets=reranked.reranked_raw_assets,
        prompt_context_assets=compressed.prompt_context_assets,
        context_compression=compressed.context_compression,
        prompt_sources=prompt_out.prompt_sources,
        image_context_enriched=prompt_out.image_context_enriched,
        multimodal_analysis=prompt_out.multimodal_analysis,
        multimodal_orchestration_hint=prompt_out.multimodal_orchestration_hint,
        raw_context=prompt_out.raw_context,
        prompt=prompt_out.prompt,
        confidence=confidence,
        latency=latency,
        latency_ms=total_pipeline_ms,
    )
