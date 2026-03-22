from __future__ import annotations

from time import perf_counter

from src.application.chat.policies.pipeline_document_selection import (
    deduplicate_summary_doc_ids,
    select_summary_documents_by_doc_ids,
)
from src.application.chat.policies.prompt_source_wire import prompt_source_to_wire_dict
from src.core.config import RETRIEVAL_CONFIG
from src.domain.pipeline_latency import PipelineLatency
from src.domain.pipeline_payloads import (
    ContextCompressionStats,
    PipelineBuildResult,
    SectionExpansionStats,
    SummaryRecallResult,
)
from src.domain.project import Project
from src.domain.prompt_source import PromptSource
from src.domain.summary_recall_document import SummaryRecallDocument
from src.infrastructure.adapters.rag.confidence_service import ConfidenceService
from src.infrastructure.adapters.rag.contextual_compression_service import ContextualCompressionService
from src.infrastructure.adapters.rag.docstore_service import DocStoreService
from src.infrastructure.adapters.rag.layout_context_service import LayoutContextService
from src.infrastructure.adapters.rag.multimodal_orchestration_service import MultimodalOrchestrationService
from src.infrastructure.adapters.rag.prompt_builder_service import PromptBuilderService
from src.infrastructure.adapters.rag.reranking_service import RerankingService
from src.infrastructure.adapters.rag.section_retrieval_service import SectionRetrievalService
from src.infrastructure.adapters.rag.prompt_source_service import PromptSourceService
from src.infrastructure.adapters.rag.table_qa_service import TableQAService


class PipelineAssemblyService:
    """
    After summary recall: rehydrate assets, expand sections, rerank, compress,
    build prompt sources, and assemble the final prompt context.
    """

    def __init__(
        self,
        docstore_service: DocStoreService,
        reranking_service: RerankingService,
        table_qa_service: TableQAService,
    ):
        self.docstore_service = docstore_service
        self.reranking_service = reranking_service
        self.table_qa_service = table_qa_service
        self.confidence_service = ConfidenceService()
        self.prompt_source_service = PromptSourceService()
        self.prompt_builder_service = PromptBuilderService(
            max_text_chars_per_asset=RETRIEVAL_CONFIG.max_text_chars_per_asset,
            max_table_chars_per_asset=RETRIEVAL_CONFIG.max_table_chars_per_asset,
        )
        self.contextual_compression_service = ContextualCompressionService()
        self.section_retrieval_service = SectionRetrievalService()
        self.layout_context_service = LayoutContextService()
        self.multimodal_orchestration_service = MultimodalOrchestrationService()

    @staticmethod
    def deduplicate_doc_ids(summary_docs: list[SummaryRecallDocument]) -> list[str]:
        return deduplicate_summary_doc_ids(summary_docs)

    @staticmethod
    def select_summary_docs_by_doc_ids(summary_docs: list, doc_ids: list[str]) -> list:
        return select_summary_documents_by_doc_ids(summary_docs, doc_ids)

    def _section_expansion_corpus(
        self,
        *,
        project: Project,
        recalled_raw_assets: list[dict],
    ) -> list[dict]:
        seen_files: set[str] = set()
        source_files: list[str] = []
        for asset in recalled_raw_assets:
            sf = asset.get("source_file")
            if not sf:
                continue
            s = str(sf).strip()
            if not s or s in seen_files:
                continue
            seen_files.add(s)
            source_files.append(s)

        if not source_files:
            return self.docstore_service.list_assets_for_project(
                user_id=project.user_id,
                project_id=project.project_id,
            )

        by_doc: dict[str, dict] = {}
        for s in source_files:
            for row in self.docstore_service.list_assets_for_source_file(
                user_id=project.user_id,
                project_id=project.project_id,
                source_file=s,
            ):
                did = row.get("doc_id")
                if did:
                    by_doc[str(did)] = row
        return list(by_doc.values())

    @staticmethod
    def prompt_source_to_dict(prompt_source: PromptSource) -> dict:
        return prompt_source_to_wire_dict(prompt_source)

    def build(
        self,
        *,
        project: Project,
        question: str,
        chat_history: list,
        recall: SummaryRecallResult,
        pipeline_started_monotonic: float,
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

        if not recalled_summary_docs:
            return None

        recalled_doc_ids = self.deduplicate_doc_ids(recalled_summary_docs)
        if not recalled_doc_ids:
            return None

        recalled_raw_assets = self.docstore_service.get_assets_by_doc_ids(recalled_doc_ids)
        if not recalled_raw_assets:
            return None

        corpus = self._section_expansion_corpus(
            project=project,
            recalled_raw_assets=recalled_raw_assets,
        )
        expansion = self.section_retrieval_service.expand(
            config=settings,
            retrieved_assets=recalled_raw_assets,
            all_assets=corpus,
        )
        pre_rerank_raw_assets = expansion.assets
        section_expansion = SectionExpansionStats(
            enabled=bool(settings.enable_section_expansion),
            applied=expansion.applied,
            section_expansion_count=expansion.section_expansion_count,
            expanded_assets_count=expansion.expanded_assets_count,
            recall_pool_size=len(recalled_raw_assets),
        )

        t0 = perf_counter()
        reranked_raw_assets = self.reranking_service.rerank(
            query=rewritten_question,
            raw_assets=pre_rerank_raw_assets,
            top_k=settings.max_prompt_assets,
            prefer_tables=table_aware_qa_enabled,
            table_boost=(
                self.table_qa_service.table_priority_boost() if table_aware_qa_enabled else 0.0
            ),
        )
        reranking_ms = (perf_counter() - t0) * 1000.0

        if not reranked_raw_assets:
            return None

        selected_doc_ids = [asset.get("doc_id") for asset in reranked_raw_assets if asset.get("doc_id")]
        selected_summary_docs = self.select_summary_docs_by_doc_ids(
            recalled_summary_docs,
            selected_doc_ids,
        )

        comp = self.contextual_compression_service
        chars_before = comp.prompt_char_estimate(reranked_raw_assets)
        prompt_context_assets = reranked_raw_assets
        compression_applied = False
        if settings.enable_contextual_compression:
            try:
                prompt_context_assets = comp.compress(
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

        t0 = perf_counter()
        prompt_source_objects = self.prompt_source_service.build_prompt_sources(
            prompt_context_assets
        )
        prompt_sources = [
            self.prompt_source_to_dict(ps) for ps in prompt_source_objects
        ]

        image_ctx_by_id, image_context_enriched = (
            self.prompt_builder_service.prepare_image_contexts(prompt_context_assets)
        )
        grouped_assets = self.layout_context_service.group_assets(prompt_context_assets)
        layout_groups_ok = self.layout_context_service.validate_groups(
            prompt_context_assets,
            grouped_assets,
        )
        asset_groups = grouped_assets if layout_groups_ok else None

        raw_context = self.prompt_builder_service.build_raw_context(
            raw_assets=prompt_context_assets,
            prompt_sources=prompt_source_objects,
            image_context_by_doc_id=image_ctx_by_id,
            asset_groups=asset_groups,
            max_text_chars_per_asset=settings.max_text_chars_per_asset,
            max_table_chars_per_asset=settings.max_table_chars_per_asset,
        )
        multimodal_analysis = self.multimodal_orchestration_service.analyze(prompt_context_assets)
        multimodal_orchestration_hint = self.multimodal_orchestration_service.build_prompt_hint(
            multimodal_analysis
        )
        prompt = self.prompt_builder_service.build_prompt(
            question=question,
            chat_history=chat_history,
            raw_context=raw_context,
            table_aware_instruction=(
                self.table_qa_service.build_table_prompt_hint()
                if table_aware_qa_enabled
                else None
            ),
            orchestration_hint=multimodal_orchestration_hint or None,
            layout_aware=bool(asset_groups),
        )
        prompt_build_ms = (perf_counter() - t0) * 1000.0

        confidence = self.confidence_service.compute_confidence(
            reranked_raw_assets=reranked_raw_assets,
        )

        retrieval_mode = "faiss+bm25" if enable_hybrid_retrieval else "faiss"

        total_pipeline_ms = (perf_counter() - pipeline_started_monotonic) * 1000.0
        latency = PipelineLatency(
            query_rewrite_ms=query_rewrite_ms,
            retrieval_ms=retrieval_ms,
            reranking_ms=reranking_ms,
            prompt_build_ms=prompt_build_ms,
            answer_generation_ms=0.0,
            total_ms=total_pipeline_ms,
        )
        latency_dict = latency.to_dict()

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
            recalled_doc_ids=recalled_doc_ids,
            recalled_raw_assets=recalled_raw_assets,
            pre_rerank_raw_assets=pre_rerank_raw_assets,
            section_expansion=section_expansion,
            selected_summary_docs=selected_summary_docs,
            selected_doc_ids=selected_doc_ids,
            reranked_raw_assets=reranked_raw_assets,
            prompt_context_assets=prompt_context_assets,
            context_compression=context_compression,
            prompt_sources=prompt_sources,
            image_context_enriched=image_context_enriched,
            multimodal_analysis=multimodal_analysis,
            multimodal_orchestration_hint=multimodal_orchestration_hint,
            raw_context=raw_context,
            prompt=prompt,
            confidence=confidence,
            latency=latency_dict,
            latency_ms=total_pipeline_ms,
        )
