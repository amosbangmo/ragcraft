from time import perf_counter
from typing import Any

from langchain_core.documents import Document

from src.core.config import LLM, RETRIEVAL_CONFIG
from src.core.exceptions import LLMServiceError
from src.domain.pipeline_latency import PipelineLatency, merge_with_answer_stage
from src.domain.pipeline_payloads import (
    ContextCompressionStats,
    PipelineBuildResult,
    SectionExpansionStats,
)
from src.domain.project import Project
from src.domain.rag_response import RAGResponse
from src.domain.retrieval_filters import RetrievalFilters
from src.domain.source_citation import SourceCitation
from src.services.confidence_service import ConfidenceService
from src.services.contextual_compression_service import ContextualCompressionService
from src.services.docstore_service import DocStoreService
from src.services.evaluation_service import EvaluationService
from src.services.layout_context_service import LayoutContextService
from src.services.multimodal_orchestration_service import MultimodalOrchestrationService
from src.services.prompt_builder_service import PromptBuilderService
from src.services.query_log_service import QueryLogService
from src.services.reranking_service import RerankingService
from src.services.retrieval_settings_service import RetrievalSettingsService
from src.services.section_retrieval_service import SectionRetrievalService
from src.services.source_citation_service import SourceCitationService
from src.services.summary_recall_service import SummaryRecallService
from src.services.table_qa_service import TableQAService
from src.services.vectorstore_service import VectorStoreService


class RAGService:
    """
    Multi-step RAG service:
    1. optional query rewriting
    2. hybrid recall retrieval (FAISS + BM25 summaries)
    3. raw asset rehydration from SQLite using doc_id
    4. optional section-aware expansion of the rerank pool (same file / section / neighbors)
    5. strict reranking over the expanded raw assets (table column headers from structured_table
       are included in reranker text when present)
    6. optional contextual compression of reranked assets for the prompt
    7. final prompt built from the compressed (or original) top assets, including structured
       table excerpts from asset metadata when ingestion populated them, and image contextual
       blocks (metadata, same-page excerpt, optional same-file text neighbors) when present
    """

    def __init__(
        self,
        vectorstore_service: VectorStoreService,
        evaluation_service: EvaluationService,
        docstore_service: DocStoreService,
        reranking_service: RerankingService,
        query_log_service: QueryLogService | None = None,
        retrieval_settings_service: RetrievalSettingsService | None = None,
    ):
        self.vectorstore_service = vectorstore_service
        self.evaluation_service = evaluation_service
        self.docstore_service = docstore_service
        self.reranking_service = reranking_service
        self.confidence_service = ConfidenceService()
        self.source_citation_service = SourceCitationService()
        self.prompt_builder_service = PromptBuilderService(
            max_text_chars_per_asset=RETRIEVAL_CONFIG.max_text_chars_per_asset,
            max_table_chars_per_asset=RETRIEVAL_CONFIG.max_table_chars_per_asset,
        )
        self.retrieval_settings_service = (
            retrieval_settings_service or RetrievalSettingsService()
        )
        self.table_qa_service = TableQAService()
        self.summary_recall_service = SummaryRecallService(
            vectorstore_service=vectorstore_service,
            docstore_service=docstore_service,
            retrieval_settings_service=self.retrieval_settings_service,
            table_qa_service=self.table_qa_service,
        )
        self.contextual_compression_service = ContextualCompressionService()
        self.query_log_service = query_log_service
        self.section_retrieval_service = SectionRetrievalService()
        self.layout_context_service = LayoutContextService()
        self.multimodal_orchestration_service = MultimodalOrchestrationService()

    @property
    def config(self) -> Any:
        """Alias for the env-backed retrieval config object (mutable in tests)."""
        return self.retrieval_settings_service.config_source

    @config.setter
    def config(self, value: Any) -> None:
        self.retrieval_settings_service.set_config_source(value)

    @staticmethod
    def _latency_fields_for_query_log(latency: PipelineLatency) -> dict:
        d = latency.to_dict()
        return {
            "query_rewrite_ms": d["query_rewrite_ms"],
            "retrieval_ms": d["retrieval_ms"],
            "reranking_ms": d["reranking_ms"],
            "prompt_build_ms": d["prompt_build_ms"],
            "answer_generation_ms": d["answer_generation_ms"],
            "total_latency_ms": d["total_ms"],
        }

    def _safe_log_query(self, payload: dict) -> None:
        if self.query_log_service is None:
            return
        try:
            self.query_log_service.log_query(payload=payload)
        except Exception:
            pass

    def build_chain(self, project: Project):
        """
        Kept only for cache compatibility with the current app state design.
        Returns the project vector store instead of a LangChain retrieval chain.
        """
        return self.vectorstore_service.load(project)

    def _deduplicate_doc_ids(self, summary_docs: list[Document]) -> list[str]:
        seen = set()
        ordered_doc_ids: list[str] = []

        for doc in summary_docs:
            doc_id = doc.metadata.get("doc_id")
            if not doc_id or doc_id in seen:
                continue
            seen.add(doc_id)
            ordered_doc_ids.append(doc_id)

        return ordered_doc_ids

    def _select_summary_docs_by_doc_ids(self, summary_docs: list, doc_ids: list[str]) -> list:
        docs_by_id = {}

        for doc in summary_docs:
            doc_id = doc.metadata.get("doc_id")
            if doc_id and doc_id not in docs_by_id:
                docs_by_id[doc_id] = doc

        return [docs_by_id[doc_id] for doc_id in doc_ids if doc_id in docs_by_id]

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

    def _citation_to_dict(self, citation: SourceCitation) -> dict:
        rerank_score = citation.metadata.get("rerank_score") if citation.metadata else None

        return {
            "source_number": citation.source_number,
            "doc_id": citation.doc_id,
            "source_file": citation.source_file,
            "content_type": citation.content_type,
            "page_label": citation.page_label,
            "locator_label": citation.locator_label,
            "display_label": citation.display_label,
            "inline_label": citation.prompt_label,
            "metadata": citation.metadata,
            "rerank_score": rerank_score,
        }

    def preview_summary_recall(
        self,
        project: Project,
        question: str,
        chat_history=None,
        *,
        filters: RetrievalFilters | None = None,
        retrieval_settings: dict[str, Any] | None = None,
        enable_query_rewrite_override: bool | None = None,
        enable_hybrid_retrieval_override: bool | None = None,
    ) -> dict | None:
        """
        Run query rewrite (if enabled) and summary recall only — for Search UI parity with chat.
        """
        if chat_history is None:
            chat_history = []

        bundle = self.summary_recall_service.summary_recall_stage(
            project,
            question,
            chat_history,
            enable_query_rewrite_override=enable_query_rewrite_override,
            enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
            filters=filters,
            retrieval_settings=retrieval_settings,
        )
        recalled = bundle.recalled_summary_docs
        if not recalled:
            return None
        return {
            "rewritten_question": bundle.rewritten_question,
            "recalled_summary_docs": recalled,
            "vector_summary_docs": bundle.vector_summary_docs,
            "bm25_summary_docs": bundle.bm25_summary_docs,
            "retrieval_mode": "faiss+bm25" if bundle.enable_hybrid_retrieval else "faiss",
            "query_rewrite_enabled": bundle.enable_query_rewrite,
            "hybrid_retrieval_enabled": bundle.enable_hybrid_retrieval,
            "use_adaptive_retrieval": bundle.use_adaptive_retrieval,
        }

    def _run_pipeline(
        self,
        project: Project,
        question: str,
        chat_history=None,
        *,
        enable_query_rewrite_override: bool | None = None,
        enable_hybrid_retrieval_override: bool | None = None,
        defer_query_log: bool = False,
        filters: RetrievalFilters | None = None,
        retrieval_settings: dict[str, Any] | None = None,
    ) -> PipelineBuildResult | None:
        pipeline_started = perf_counter()
        if chat_history is None:
            chat_history = []

        bundle = self.summary_recall_service.summary_recall_stage(
            project,
            question,
            chat_history,
            enable_query_rewrite_override=enable_query_rewrite_override,
            enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
            filters=filters,
            retrieval_settings=retrieval_settings,
        )

        settings = bundle.settings
        query_rewrite_ms = bundle.query_rewrite_ms
        query_intent = bundle.query_intent
        table_aware_qa_enabled = bundle.table_aware_qa_enabled
        use_adaptive_retrieval = bundle.use_adaptive_retrieval
        strategy = bundle.strategy
        enable_hybrid_retrieval = bundle.enable_hybrid_retrieval
        filters_for_retrieval = bundle.filters_for_retrieval
        retrieval_ms = bundle.retrieval_ms
        rewritten_question = bundle.rewritten_question
        enable_query_rewrite = bundle.enable_query_rewrite

        vector_summary_docs = bundle.vector_summary_docs
        bm25_summary_docs = bundle.bm25_summary_docs
        recalled_summary_docs = bundle.recalled_summary_docs

        if not recalled_summary_docs:
            return None

        recalled_doc_ids = self._deduplicate_doc_ids(recalled_summary_docs)
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
        selected_summary_docs = self._select_summary_docs_by_doc_ids(
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
        citation_objects = self.source_citation_service.build_citations(prompt_context_assets)
        source_references = [self._citation_to_dict(citation) for citation in citation_objects]

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
            citations=citation_objects,
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

        total_pipeline_ms = (perf_counter() - pipeline_started) * 1000.0
        latency = PipelineLatency(
            query_rewrite_ms=query_rewrite_ms,
            retrieval_ms=retrieval_ms,
            reranking_ms=reranking_ms,
            prompt_build_ms=prompt_build_ms,
            answer_generation_ms=0.0,
            total_ms=total_pipeline_ms,
        )
        latency_dict = latency.to_dict()

        payload = PipelineBuildResult(
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
            source_references=source_references,
            image_context_enriched=image_context_enriched,
            multimodal_analysis=multimodal_analysis,
            multimodal_orchestration_hint=multimodal_orchestration_hint,
            raw_context=raw_context,
            prompt=prompt,
            confidence=confidence,
            latency=latency_dict,
            latency_ms=total_pipeline_ms,
        )

        if self.query_log_service is not None and not defer_query_log:
            self._safe_log_query(
                {
                    "question": question,
                    "rewritten_query": rewritten_question,
                    "project_id": project.project_id,
                    "user_id": project.user_id,
                    "selected_doc_ids": selected_doc_ids,
                    "retrieved_doc_ids": recalled_doc_ids,
                    "latency_ms": latency.total_ms,
                    "confidence": confidence,
                    "hybrid_retrieval_enabled": enable_hybrid_retrieval,
                    "retrieval_mode": retrieval_mode,
                    "query_intent": query_intent.value,
                    "table_aware_qa_enabled": table_aware_qa_enabled,
                    "retrieval_strategy": strategy.to_dict(),
                    "context_compression_chars_before": context_compression.chars_before,
                    "context_compression_chars_after": context_compression.chars_after,
                    "context_compression_ratio": context_compression.ratio,
                    "section_expansion_count": section_expansion.section_expansion_count,
                    "expanded_assets_count": section_expansion.expanded_assets_count,
                    **self._latency_fields_for_query_log(latency),
                }
            )

        return payload

    def inspect_pipeline(
        self,
        project: Project,
        question: str,
        chat_history=None,
        *,
        enable_query_rewrite_override: bool | None = None,
        enable_hybrid_retrieval_override: bool | None = None,
        filters: RetrievalFilters | None = None,
        retrieval_settings: dict[str, Any] | None = None,
    ) -> PipelineBuildResult | None:
        return self._run_pipeline(
            project,
            question,
            chat_history,
            enable_query_rewrite_override=enable_query_rewrite_override,
            enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
            defer_query_log=True,
            filters=filters,
            retrieval_settings=retrieval_settings,
        )

    def generate_answer_from_pipeline(self, *, project: Project, pipeline: PipelineBuildResult) -> str:
        """
        Generate the final answer from an already-prepared pipeline payload.

        This keeps dataset evaluation and interactive chat aligned on the exact
        same answer generation logic without duplicating LLM invocation code.
        """
        try:
            response = LLM.invoke(pipeline.prompt)
        except Exception as exc:
            raise LLMServiceError(
                f"Failed to generate answer for project '{project.project_id}': {exc}",
                user_message="The language model failed while generating the answer.",
            ) from exc

        return getattr(response, "content", str(response)).strip()

    def ask(
        self,
        project: Project,
        question: str,
        chat_history=None,
        *,
        filters: RetrievalFilters | None = None,
        retrieval_settings: dict[str, Any] | None = None,
        enable_query_rewrite_override: bool | None = None,
        enable_hybrid_retrieval_override: bool | None = None,
    ) -> RAGResponse | None:
        ask_started = perf_counter()
        defer_log = self.query_log_service is not None
        pipeline = self._run_pipeline(
            project,
            question,
            chat_history,
            defer_query_log=defer_log,
            filters=filters,
            retrieval_settings=retrieval_settings,
            enable_query_rewrite_override=enable_query_rewrite_override,
            enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
        )

        if pipeline is None:
            return None

        gen_started = perf_counter()
        answer = self.generate_answer_from_pipeline(project=project, pipeline=pipeline)
        answer_generation_ms = (perf_counter() - gen_started) * 1000.0
        total_ms = (perf_counter() - ask_started) * 1000.0
        full_latency = merge_with_answer_stage(
            pipeline.latency,
            answer_generation_ms=answer_generation_ms,
            total_ms=total_ms,
        )
        full_latency_dict = full_latency.to_dict()
        pipeline.latency = full_latency_dict
        pipeline.latency_ms = total_ms

        if defer_log:
            self._safe_log_query(
                {
                    "question": question,
                    "rewritten_query": pipeline.rewritten_question,
                    "project_id": project.project_id,
                    "user_id": project.user_id,
                    "selected_doc_ids": pipeline.selected_doc_ids,
                    "retrieved_doc_ids": pipeline.recalled_doc_ids,
                    "latency_ms": total_ms,
                    "confidence": pipeline.confidence,
                    "answer": answer,
                    "hybrid_retrieval_enabled": pipeline.hybrid_retrieval_enabled,
                    "retrieval_mode": pipeline.retrieval_mode,
                    "query_intent": pipeline.query_intent.value,
                    "table_aware_qa_enabled": pipeline.table_aware_qa_enabled,
                    "retrieval_strategy": pipeline.retrieval_strategy.to_dict(),
                    "context_compression_chars_before": pipeline.context_compression.chars_before,
                    "context_compression_chars_after": pipeline.context_compression.chars_after,
                    "context_compression_ratio": pipeline.context_compression.ratio,
                    "section_expansion_count": pipeline.section_expansion.section_expansion_count,
                    "expanded_assets_count": pipeline.section_expansion.expanded_assets_count,
                    **self._latency_fields_for_query_log(full_latency),
                }
            )

        return RAGResponse(
            question=question,
            answer=answer,
            source_documents=pipeline.selected_summary_docs,
            raw_assets=pipeline.reranked_raw_assets,
            citations=pipeline.source_references,
            confidence=pipeline.confidence,
            latency=full_latency_dict,
        )
