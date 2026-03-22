from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from src.domain.pipeline_payloads import (
    PipelineBuildResult,
    SectionExpansionPoolResult,
    SummaryRecallResult,
)
from src.domain.project import Project
from src.domain.prompt_source import PromptSource
from src.domain.retrieval_filters import RetrievalFilters
from src.domain.retrieval_settings import RetrievalSettings


class SummaryRecallStagePort(Protocol):
    def summary_recall_stage(
        self,
        project: Project,
        question: str,
        chat_history: list[str],
        *,
        enable_query_rewrite_override: bool | None,
        enable_hybrid_retrieval_override: bool | None,
        filters: RetrievalFilters | None,
        retrieval_settings: dict[str, Any] | None,
    ) -> SummaryRecallResult: ...


class PipelineAssemblyPort(Protocol):
    def build(
        self,
        *,
        project: Project,
        question: str,
        chat_history: list[str],
        recall: SummaryRecallResult,
        pipeline_started_monotonic: float,
    ) -> PipelineBuildResult | None: ...


class DocstoreRecallReadPort(Protocol):
    """Hydrate and list raw assets for post-recall assembly."""

    def get_assets_by_doc_ids(self, doc_ids: list[str]) -> list[dict]: ...

    def list_assets_for_project(self, *, user_id: str, project_id: str) -> list[dict]: ...

    def list_assets_for_source_file(
        self, *, user_id: str, project_id: str, source_file: str
    ) -> list[dict]: ...


class SectionExpansionStagePort(Protocol):
    def expand_section_pool(
        self,
        *,
        settings: RetrievalSettings,
        retrieved_assets: list[dict],
        all_assets: list[dict],
    ) -> SectionExpansionPoolResult: ...


class AssetRerankingPort(Protocol):
    def rerank_assets(
        self,
        *,
        query: str,
        raw_assets: list[dict],
        top_k: int,
        prefer_tables: bool,
        table_boost: float,
    ) -> list[dict]: ...


class TableQaAdjunctPort(Protocol):
    def table_priority_boost(self) -> float: ...

    def build_table_prompt_hint(self) -> str: ...


class ContextualCompressionPort(Protocol):
    def prompt_char_estimate(self, assets: list[dict]) -> float: ...

    def compress_assets(self, *, query: str, assets: list[dict]) -> list[dict]: ...


class PromptSourceBuildPort(Protocol):
    def build_prompt_sources(self, prompt_context_assets: list[dict]) -> list[PromptSource]: ...


class LayoutGroupingPort(Protocol):
    def group_assets(self, assets: list[dict]) -> list[list[dict]]: ...

    def validate_layout_groups(self, assets: list[dict], groups: list[list[dict]]) -> bool: ...


class MultimodalPromptHintPort(Protocol):
    def analyze_modalities(self, prompt_context_assets: list[dict]) -> dict: ...

    def build_multimodal_prompt_hint(self, multimodal_analysis: dict) -> str: ...


class PromptRenderPort(Protocol):
    def prepare_image_contexts(
        self, prompt_context_assets: list[dict]
    ) -> tuple[dict[str, dict], bool]: ...

    def build_raw_context(
        self,
        *,
        raw_assets: list[dict],
        prompt_sources: list[PromptSource],
        image_context_by_doc_id: dict[str, dict],
        asset_groups: list[list[dict]] | None,
        max_text_chars_per_asset: int,
        max_table_chars_per_asset: int,
    ) -> str: ...

    def build_answer_prompt(
        self,
        *,
        question: str,
        chat_history: list[str],
        raw_context: str,
        table_aware_instruction: str | None,
        orchestration_hint: str | None,
        layout_aware: bool,
    ) -> str: ...


class RerankedConfidencePort(Protocol):
    def compute_confidence(self, *, reranked_raw_assets: list[dict]) -> float: ...


@dataclass(frozen=True)
class PostRecallStagePorts:
    """Injected technical ports for post-recall assembly (see ``assemble_pipeline_from_recall``)."""

    docstore_read: DocstoreRecallReadPort
    section_expansion: SectionExpansionStagePort
    reranking: AssetRerankingPort
    table_qa: TableQaAdjunctPort
    contextual_compression: ContextualCompressionPort
    prompt_sources: PromptSourceBuildPort
    layout_grouping: LayoutGroupingPort
    multimodal_hints: MultimodalPromptHintPort
    prompt_render: PromptRenderPort
    confidence: RerankedConfidencePort
