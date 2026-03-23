"""
Narrow infrastructure adapters for post–summary-recall pipeline stages.

Orchestration order lives in :mod:`application.use_cases.chat.orchestration.assemble_pipeline_from_recall`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from domain.rag.pipeline_payloads import SectionExpansionPoolResult
from domain.rag.prompt_source import PromptSource
from domain.rag.retrieval_settings import RetrievalSettings
from infrastructure.config.config import RETRIEVAL_CONFIG
from infrastructure.rag.confidence_service import ConfidenceService
from infrastructure.rag.contextual_compression_service import ContextualCompressionService
from infrastructure.rag.docstore_service import DocStoreService
from infrastructure.rag.layout_context_service import LayoutContextService
from infrastructure.rag.prompt_builder_service import PromptBuilderService
from infrastructure.rag.prompt_source_service import PromptSourceService
from infrastructure.rag.reranking_service import RerankingService
from infrastructure.rag.section_retrieval_service import SectionRetrievalService
from infrastructure.rag.table_qa_service import TableQAService


class MultimodalPromptHintsLike(Protocol):
    """Structural type for :class:`~application.chat.multimodal_prompt_hints.MultimodalPromptHints` (wired in composition)."""

    def analyze_modalities(self, prompt_context_assets: list[dict]) -> dict: ...

    def build_multimodal_prompt_hint(self, multimodal_analysis: dict) -> str: ...


class DocstoreRecallReadAdapter:
    def __init__(self, docstore: DocStoreService) -> None:
        self._docstore = docstore

    def get_assets_by_doc_ids(self, doc_ids: list[str]) -> list[dict]:
        return self._docstore.get_assets_by_doc_ids(doc_ids)

    def list_assets_for_project(self, *, user_id: str, project_id: str) -> list[dict]:
        return self._docstore.list_assets_for_project(user_id=user_id, project_id=project_id)

    def list_assets_for_source_file(
        self, *, user_id: str, project_id: str, source_file: str
    ) -> list[dict]:
        return self._docstore.list_assets_for_source_file(
            user_id=user_id,
            project_id=project_id,
            source_file=source_file,
        )


class SectionExpansionStageAdapter:
    def __init__(self, section_retrieval: SectionRetrievalService) -> None:
        self._section = section_retrieval

    def expand_section_pool(
        self,
        *,
        settings: RetrievalSettings,
        retrieved_assets: list[dict],
        all_assets: list[dict],
    ) -> SectionExpansionPoolResult:
        r = self._section.expand(
            config=settings,
            retrieved_assets=retrieved_assets,
            all_assets=all_assets,
        )
        return SectionExpansionPoolResult(
            assets=r.assets,
            applied=r.applied,
            section_expansion_count=r.section_expansion_count,
            expanded_assets_count=r.expanded_assets_count,
        )


class AssetRerankingAdapter:
    def __init__(self, reranking: RerankingService) -> None:
        self._rerank = reranking

    def rerank_assets(
        self,
        *,
        query: str,
        raw_assets: list[dict],
        top_k: int,
        prefer_tables: bool,
        table_boost: float,
    ) -> list[dict]:
        return self._rerank.rerank(
            query,
            raw_assets,
            top_k,
            prefer_tables=prefer_tables,
            table_boost=table_boost,
        )


class TableQaAdjunctAdapter:
    def __init__(self, table_qa: TableQAService) -> None:
        self._table_qa = table_qa

    def table_priority_boost(self) -> float:
        return self._table_qa.table_priority_boost()

    def build_table_prompt_hint(self) -> str:
        return self._table_qa.build_table_prompt_hint()


class ContextualCompressionAdapter:
    def __init__(self, compression: ContextualCompressionService) -> None:
        self._c = compression

    def prompt_char_estimate(self, assets: list[dict]) -> float:
        return self._c.prompt_char_estimate(assets)

    def compress_assets(self, *, query: str, assets: list[dict]) -> list[dict]:
        return self._c.compress(query=query, assets=assets)


class PromptSourceBuildAdapter:
    def __init__(self, prompt_sources: PromptSourceService) -> None:
        self._ps = prompt_sources

    def build_prompt_sources(self, prompt_context_assets: list[dict]) -> list[PromptSource]:
        return self._ps.build_prompt_sources(prompt_context_assets)


class LayoutGroupingAdapter:
    def __init__(self, layout: LayoutContextService) -> None:
        self._layout = layout

    def group_assets(self, assets: list[dict]) -> list[list[dict]]:
        return self._layout.group_assets(assets)

    def validate_layout_groups(self, assets: list[dict], groups: list[list[dict]]) -> bool:
        return self._layout.validate_groups(assets, groups)


class PromptRenderAdapter:
    def __init__(self, builder: PromptBuilderService) -> None:
        self._b = builder

    def prepare_image_contexts(
        self, prompt_context_assets: list[dict]
    ) -> tuple[dict[str, dict], bool]:
        return self._b.prepare_image_contexts(prompt_context_assets)

    def build_raw_context(
        self,
        *,
        raw_assets: list[dict],
        prompt_sources: list[PromptSource],
        image_context_by_doc_id: dict[str, dict],
        asset_groups: list[list[dict]] | None,
        max_text_chars_per_asset: int,
        max_table_chars_per_asset: int,
    ) -> str:
        return self._b.build_raw_context(
            raw_assets=raw_assets,
            prompt_sources=prompt_sources,
            image_context_by_doc_id=image_context_by_doc_id,
            asset_groups=asset_groups,
            max_text_chars_per_asset=max_text_chars_per_asset,
            max_table_chars_per_asset=max_table_chars_per_asset,
        )

    def build_answer_prompt(
        self,
        *,
        question: str,
        chat_history: list[str],
        raw_context: str,
        table_aware_instruction: str | None,
        orchestration_hint: str | None,
        layout_aware: bool,
    ) -> str:
        return self._b.build_prompt(
            question=question,
            chat_history=chat_history,
            raw_context=raw_context,
            table_aware_instruction=table_aware_instruction,
            orchestration_hint=orchestration_hint,
            layout_aware=layout_aware,
        )


class RerankedConfidenceAdapter:
    def __init__(self, confidence: ConfidenceService) -> None:
        self._c = confidence

    def compute_confidence(self, *, reranked_raw_assets: list[dict]) -> float:
        return self._c.compute_confidence(reranked_raw_assets=reranked_raw_assets)


@dataclass
class PostRecallStageServices:
    """Concrete services for composition and targeted test patching."""

    docstore_service: DocStoreService
    reranking_service: RerankingService
    table_qa_service: TableQAService
    section_retrieval_service: SectionRetrievalService
    contextual_compression_service: ContextualCompressionService
    prompt_source_service: PromptSourceService
    prompt_builder_service: PromptBuilderService
    layout_context_service: LayoutContextService
    multimodal_prompt_hints: MultimodalPromptHintsLike
    confidence_service: ConfidenceService


def build_post_recall_stage_services(
    *,
    docstore_service: DocStoreService,
    reranking_service: RerankingService,
    table_qa_service: TableQAService,
    multimodal_prompt_hints: MultimodalPromptHintsLike,
) -> PostRecallStageServices:
    prompt_builder = PromptBuilderService(
        max_text_chars_per_asset=RETRIEVAL_CONFIG.max_text_chars_per_asset,
        max_table_chars_per_asset=RETRIEVAL_CONFIG.max_table_chars_per_asset,
    )
    return PostRecallStageServices(
        docstore_service=docstore_service,
        reranking_service=reranking_service,
        table_qa_service=table_qa_service,
        section_retrieval_service=SectionRetrievalService(),
        contextual_compression_service=ContextualCompressionService(),
        prompt_source_service=PromptSourceService(),
        prompt_builder_service=prompt_builder,
        layout_context_service=LayoutContextService(),
        multimodal_prompt_hints=multimodal_prompt_hints,
        confidence_service=ConfidenceService(),
    )
