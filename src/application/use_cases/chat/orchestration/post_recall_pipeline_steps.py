"""
Explicit post–summary-recall steps (application orchestration).

Each step delegates to a port on :class:`~src.application.use_cases.chat.orchestration.ports.PostRecallStagePorts`.
Ordering is owned here; adapters implement technical work only.
"""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any

from src.application.chat.policies.pipeline_document_selection import (
    deduplicate_summary_doc_ids,
    select_summary_documents_by_doc_ids,
)
from src.application.chat.policies.prompt_source_wire import prompt_source_to_wire_dict
from src.application.use_cases.chat.orchestration.ports import PostRecallStagePorts
from src.application.use_cases.chat.orchestration.section_expansion_corpus import (
    build_section_expansion_corpus,
)
from src.domain.pipeline_payloads import (
    ContextCompressionStats,
    SectionExpansionPoolResult,
    SectionExpansionStats,
    SummaryRecallResult,
)
from src.domain.project import Project
from src.domain.retrieval_settings import RetrievalSettings


@dataclass(frozen=True)
class DocstoreHydrationOutcome:
    recalled_doc_ids: list[str]
    recalled_raw_assets: list[dict]


@dataclass(frozen=True)
class ExpansionOutcome:
    pre_rerank_raw_assets: list[dict]
    section_expansion: SectionExpansionStats


@dataclass(frozen=True)
class RerankOutcome:
    reranked_raw_assets: list[dict]
    selected_summary_docs: list[Any]
    selected_doc_ids: list[Any]
    reranking_ms: float


@dataclass(frozen=True)
class CompressionOutcome:
    prompt_context_assets: list[dict]
    context_compression: ContextCompressionStats


@dataclass(frozen=True)
class PromptAssemblyOutcome:
    prompt_sources: list[dict]
    image_context_enriched: bool
    multimodal_analysis: dict
    multimodal_orchestration_hint: str
    raw_context: str
    prompt: str
    prompt_build_ms: float


def step_docstore_hydration(
    *,
    project: Project,
    recall: SummaryRecallResult,
    stages: PostRecallStagePorts,
) -> DocstoreHydrationOutcome | None:
    """Rehydrate full raw assets from docstore using recalled summary doc ids."""
    recalled_summary_docs = recall.recalled_summary_docs
    if not recalled_summary_docs:
        return None
    recalled_doc_ids = deduplicate_summary_doc_ids(recalled_summary_docs)
    if not recalled_doc_ids:
        return None
    recalled_raw_assets = stages.docstore_read.get_assets_by_doc_ids(recalled_doc_ids)
    if not recalled_raw_assets:
        return None
    return DocstoreHydrationOutcome(
        recalled_doc_ids=recalled_doc_ids,
        recalled_raw_assets=recalled_raw_assets,
    )


def step_section_expansion(
    *,
    project: Project,
    settings: RetrievalSettings,
    recalled_raw_assets: list[dict],
    stages: PostRecallStagePorts,
) -> ExpansionOutcome:
    """Build expansion corpus and widen the asset pool when section expansion is enabled."""
    corpus = build_section_expansion_corpus(
        project=project,
        recalled_raw_assets=recalled_raw_assets,
        docstore=stages.docstore_read,
    )
    expansion: SectionExpansionPoolResult = stages.section_expansion.expand_section_pool(
        settings=settings,
        retrieved_assets=recalled_raw_assets,
        all_assets=corpus,
    )
    section_expansion = SectionExpansionStats(
        enabled=bool(settings.enable_section_expansion),
        applied=expansion.applied,
        section_expansion_count=expansion.section_expansion_count,
        expanded_assets_count=expansion.expanded_assets_count,
        recall_pool_size=len(recalled_raw_assets),
    )
    return ExpansionOutcome(
        pre_rerank_raw_assets=expansion.assets,
        section_expansion=section_expansion,
    )


def step_rerank_and_select_summaries(
    *,
    recall: SummaryRecallResult,
    pre_rerank_raw_assets: list[dict],
    stages: PostRecallStagePorts,
) -> RerankOutcome | None:
    """Rerank expanded pool and align summary documents with selected doc ids."""
    settings = recall.settings
    rewritten_question = recall.rewritten_question
    table_aware_qa_enabled = recall.table_aware_qa_enabled

    t0 = perf_counter()
    reranked_raw_assets = stages.reranking.rerank_assets(
        query=rewritten_question,
        raw_assets=pre_rerank_raw_assets,
        top_k=settings.max_prompt_assets,
        prefer_tables=table_aware_qa_enabled,
        table_boost=(
            stages.table_qa.table_priority_boost() if table_aware_qa_enabled else 0.0
        ),
    )
    reranking_ms = (perf_counter() - t0) * 1000.0

    if not reranked_raw_assets:
        return None

    selected_doc_ids = [
        asset.get("doc_id") for asset in reranked_raw_assets if asset.get("doc_id")
    ]
    selected_summary_docs = select_summary_documents_by_doc_ids(
        recall.recalled_summary_docs,
        selected_doc_ids,
    )
    return RerankOutcome(
        reranked_raw_assets=reranked_raw_assets,
        selected_summary_docs=selected_summary_docs,
        selected_doc_ids=selected_doc_ids,
        reranking_ms=reranking_ms,
    )


def step_contextual_compression(
    *,
    recall: SummaryRecallResult,
    reranked_raw_assets: list[dict],
    stages: PostRecallStagePorts,
) -> CompressionOutcome:
    """Optional contextual compression before prompt construction."""
    settings = recall.settings
    rewritten_question = recall.rewritten_question
    comp = stages.contextual_compression

    chars_before = comp.prompt_char_estimate(reranked_raw_assets)
    prompt_context_assets = reranked_raw_assets
    compression_applied = False
    if settings.enable_contextual_compression:
        try:
            prompt_context_assets = comp.compress_assets(
                query=rewritten_question,
                assets=reranked_raw_assets,
            )
            compression_applied = True
        except Exception:
            prompt_context_assets = reranked_raw_assets

    chars_after = comp.prompt_char_estimate(prompt_context_assets)
    ratio = (chars_after / chars_before) if chars_before > 0 else 1.0
    context_compression = ContextCompressionStats(
        enabled=bool(settings.enable_contextual_compression),
        applied=compression_applied and bool(settings.enable_contextual_compression),
        chars_before=chars_before,
        chars_after=chars_after,
        ratio=round(ratio, 4),
    )
    return CompressionOutcome(
        prompt_context_assets=prompt_context_assets,
        context_compression=context_compression,
    )


def step_prompt_assembly(
    *,
    question: str,
    chat_history: list[str],
    recall: SummaryRecallResult,
    prompt_context_assets: list[dict],
    stages: PostRecallStagePorts,
) -> PromptAssemblyOutcome:
    """
    Prompt sources, image context, layout grouping, raw context, multimodal hints, final prompt.
    """
    settings = recall.settings
    table_aware_qa_enabled = recall.table_aware_qa_enabled

    t0 = perf_counter()
    prompt_source_objects = stages.prompt_sources.build_prompt_sources(prompt_context_assets)
    prompt_sources = [prompt_source_to_wire_dict(ps) for ps in prompt_source_objects]

    image_ctx_by_id, image_context_enriched = stages.prompt_render.prepare_image_contexts(
        prompt_context_assets
    )
    grouped_assets = stages.layout_grouping.group_assets(prompt_context_assets)
    layout_groups_ok = stages.layout_grouping.validate_layout_groups(
        prompt_context_assets,
        grouped_assets,
    )
    asset_groups = grouped_assets if layout_groups_ok else None

    raw_context = stages.prompt_render.build_raw_context(
        raw_assets=prompt_context_assets,
        prompt_sources=prompt_source_objects,
        image_context_by_doc_id=image_ctx_by_id,
        asset_groups=asset_groups,
        max_text_chars_per_asset=settings.max_text_chars_per_asset,
        max_table_chars_per_asset=settings.max_table_chars_per_asset,
    )
    multimodal_analysis = stages.multimodal_hints.analyze_modalities(prompt_context_assets)
    multimodal_orchestration_hint = stages.multimodal_hints.build_multimodal_prompt_hint(
        multimodal_analysis
    )
    prompt = stages.prompt_render.build_answer_prompt(
        question=question,
        chat_history=chat_history,
        raw_context=raw_context,
        table_aware_instruction=(
            stages.table_qa.build_table_prompt_hint() if table_aware_qa_enabled else None
        ),
        orchestration_hint=multimodal_orchestration_hint or None,
        layout_aware=bool(asset_groups),
    )
    prompt_build_ms = (perf_counter() - t0) * 1000.0

    return PromptAssemblyOutcome(
        prompt_sources=prompt_sources,
        image_context_enriched=image_context_enriched,
        multimodal_analysis=multimodal_analysis,
        multimodal_orchestration_hint=multimodal_orchestration_hint,
        raw_context=raw_context,
        prompt=prompt,
        prompt_build_ms=prompt_build_ms,
    )


def step_confidence(
    *,
    reranked_raw_assets: list[dict],
    stages: PostRecallStagePorts,
) -> float:
    return stages.confidence.compute_confidence(reranked_raw_assets=reranked_raw_assets)
