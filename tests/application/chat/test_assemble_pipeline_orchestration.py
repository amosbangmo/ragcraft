"""Prove post-recall sequencing is driven from application orchestration + injected ports."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.application.use_cases.chat.orchestration.assemble_pipeline_from_recall import (
    assemble_pipeline_from_recall,
)
from src.application.use_cases.chat.orchestration.ports import PostRecallStagePorts
from src.domain.pipeline_payloads import SectionExpansionPoolResult, SummaryRecallResult
from src.domain.project import Project
from src.domain.query_intent import QueryIntent
from src.domain.retrieval_settings import RetrievalSettings
from src.domain.retrieval_strategy import RetrievalStrategy
from src.domain.summary_recall_document import SummaryRecallDocument


def _minimal_settings() -> RetrievalSettings:
    return RetrievalSettings(
        enable_query_rewrite=True,
        enable_hybrid_retrieval=False,
        similarity_search_k=5,
        bm25_search_k=5,
        hybrid_search_k=5,
        max_prompt_assets=5,
        bm25_k1=1.5,
        bm25_b=0.75,
        bm25_epsilon=0.25,
        rrf_k=60,
        hybrid_beta=0.5,
        max_text_chars_per_asset=4000,
        max_table_chars_per_asset=4000,
        query_rewrite_max_history_messages=6,
        enable_contextual_compression=False,
        enable_section_expansion=False,
        section_expansion_neighbor_window=2,
        section_expansion_max_per_section=12,
        section_expansion_global_max=64,
    )


def test_assemble_pipeline_invokes_stages_in_order() -> None:
    """Orchestration function should call stage ports in the expected pipeline order."""
    order: list[str] = []

    def _append(name: str, value):
        def _fn(*_a, **_k):
            order.append(name)
            return value

        return _fn

    docstore = MagicMock()
    docstore.get_assets_by_doc_ids.side_effect = _append(
        "docstore.get_assets_by_doc_ids",
        [{"doc_id": "d1", "raw_content": "x"}],
    )
    docstore.list_assets_for_project.side_effect = _append("docstore.list_assets_for_project", [])

    section = MagicMock()
    section.expand_section_pool.side_effect = _append(
        "section.expand_section_pool",
        SectionExpansionPoolResult(
            assets=[{"doc_id": "d1"}],
            applied=False,
            section_expansion_count=0,
            expanded_assets_count=1,
        ),
    )

    reranking = MagicMock()
    reranking.rerank_assets.side_effect = _append(
        "reranking.rerank_assets",
        [{"doc_id": "d1", "metadata": {}}],
    )

    table_qa = MagicMock()
    table_qa.table_priority_boost.return_value = 0.0
    table_qa.build_table_prompt_hint.return_value = ""

    compression = MagicMock()

    def _char_est(*_a, **_k):
        order.append("compression.prompt_char_estimate")
        return 10.0

    compression.prompt_char_estimate.side_effect = _char_est

    prompt_sources = MagicMock()
    prompt_sources.build_prompt_sources.side_effect = _append("prompt_sources.build_prompt_sources", [])

    layout = MagicMock()
    layout.group_assets.side_effect = _append("layout.group_assets", [])
    layout.validate_layout_groups.side_effect = _append("layout.validate_layout_groups", False)

    multimodal = MagicMock()
    multimodal.analyze_modalities.side_effect = _append("multimodal.analyze_modalities", {})
    multimodal.build_multimodal_prompt_hint.side_effect = _append(
        "multimodal.build_multimodal_prompt_hint",
        "",
    )

    render = MagicMock()
    render.prepare_image_contexts.side_effect = _append("render.prepare_image_contexts", ({}, False))
    render.build_raw_context.side_effect = _append("render.build_raw_context", "ctx")
    render.build_answer_prompt.side_effect = _append("render.build_answer_prompt", "prompt")

    confidence = MagicMock()
    confidence.compute_confidence.side_effect = _append("confidence.compute_confidence", 0.5)

    stages = PostRecallStagePorts(
        docstore_read=docstore,
        section_expansion=section,
        reranking=reranking,
        table_qa=table_qa,
        contextual_compression=compression,
        prompt_sources=prompt_sources,
        layout_grouping=layout,
        multimodal_hints=multimodal,
        prompt_render=render,
        confidence=confidence,
    )

    doc = SummaryRecallDocument(page_content="s", metadata={"doc_id": "d1"})
    recall = SummaryRecallResult(
        settings=_minimal_settings(),
        rewritten_question="rq",
        query_rewrite_ms=0.0,
        query_intent=QueryIntent.FACTUAL,
        table_aware_qa_enabled=False,
        use_adaptive_retrieval=False,
        strategy=RetrievalStrategy(k=5, use_hybrid=False, apply_filters=True),
        enable_hybrid_retrieval=False,
        enable_query_rewrite=True,
        filters_for_retrieval=None,
        vector_summary_docs=[doc],
        bm25_summary_docs=[],
        recalled_summary_docs=[doc],
        retrieval_ms=0.0,
    )

    project = Project(user_id="u", project_id="p")
    out = assemble_pipeline_from_recall(
        project=project,
        question="q",
        chat_history=[],
        recall=recall,
        pipeline_started_monotonic=0.0,
        stages=stages,
    )

    assert out is not None
    assert out.prompt == "prompt"

    expected = [
        "docstore.get_assets_by_doc_ids",
        "docstore.list_assets_for_project",
        "section.expand_section_pool",
        "reranking.rerank_assets",
        "compression.prompt_char_estimate",
        "compression.prompt_char_estimate",
        "prompt_sources.build_prompt_sources",
        "render.prepare_image_contexts",
        "layout.group_assets",
        "layout.validate_layout_groups",
        "render.build_raw_context",
        "multimodal.analyze_modalities",
        "multimodal.build_multimodal_prompt_hint",
        "render.build_answer_prompt",
        "confidence.compute_confidence",
    ]
    assert order == expected
