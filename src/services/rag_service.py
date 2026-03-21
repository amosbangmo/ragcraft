import logging
from dataclasses import replace
from time import perf_counter
from typing import Any

from langchain_core.documents import Document

from src.core.config import LLM, RETRIEVAL_CONFIG
from src.core.exceptions import LLMServiceError
from src.domain.pipeline_latency import PipelineLatency, merge_with_answer_stage
from src.domain.project import Project
from src.domain.rag_response import RAGResponse
from src.domain.retrieval_filters import (
    RetrievalFilters,
    filter_summary_documents_by_filters,
    vector_search_fetch_k,
)
from src.domain.retrieval_settings import RetrievalSettings
from src.domain.retrieval_strategy import RetrievalStrategy
from src.domain.source_citation import SourceCitation
from src.services.adaptive_retrieval_service import AdaptiveRetrievalService
from src.services.confidence_service import ConfidenceService
from src.services.contextual_compression_service import ContextualCompressionService
from src.services.docstore_service import DocStoreService
from src.services.evaluation_service import EvaluationService
from src.services.hybrid_retrieval_service import HybridRetrievalService
from src.services.layout_context_service import LayoutContextService
from src.services.multimodal_orchestration_service import MultimodalOrchestrationService
from src.services.prompt_builder_service import PromptBuilderService
from src.services.query_intent_service import QueryIntentService
from src.services.query_log_service import QueryLogService
from src.services.query_rewrite_service import QueryRewriteService
from src.services.reranking_service import RerankingService
from src.services.retrieval_settings_service import RetrievalSettingsService
from src.services.section_retrieval_service import SectionRetrievalService
from src.services.source_citation_service import SourceCitationService
from src.services.table_qa_service import TableQAService
from src.services.vectorstore_service import VectorStoreService

logger = logging.getLogger(__name__)


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
        self.query_rewrite_service = QueryRewriteService(
            max_history_messages=RETRIEVAL_CONFIG.query_rewrite_max_history_messages
        )
        self.hybrid_retrieval_service = HybridRetrievalService(
            k1=RETRIEVAL_CONFIG.bm25_k1,
            b=RETRIEVAL_CONFIG.bm25_b,
            epsilon=RETRIEVAL_CONFIG.bm25_epsilon,
        )
        self.prompt_builder_service = PromptBuilderService(
            max_text_chars_per_asset=RETRIEVAL_CONFIG.max_text_chars_per_asset,
            max_table_chars_per_asset=RETRIEVAL_CONFIG.max_table_chars_per_asset,
        )
        self.query_intent_service = QueryIntentService()
        self.table_qa_service = TableQAService()
        self.adaptive_retrieval_service = AdaptiveRetrievalService()
        self.contextual_compression_service = ContextualCompressionService()
        self.query_log_service = query_log_service
        self.section_retrieval_service = SectionRetrievalService()
        self.layout_context_service = LayoutContextService()
        self.multimodal_orchestration_service = MultimodalOrchestrationService()
        self.retrieval_settings_service = (
            retrieval_settings_service or RetrievalSettingsService()
        )

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

    def _rewrite_question(
        self,
        question: str,
        chat_history: list[str],
        *,
        enable_query_rewrite: bool,
        settings: RetrievalSettings,
    ) -> str:
        if not enable_query_rewrite:
            return question

        return self.query_rewrite_service.rewrite(
            question=question,
            chat_history=chat_history,
            max_history_messages=settings.query_rewrite_max_history_messages,
        )

    def _merge_summary_docs(
        self,
        *,
        settings: RetrievalSettings,
        primary_docs: list[Document],
        secondary_docs: list[Document],
        max_docs: int | None = None,
    ) -> list[Document]:
        """
        Merge two ranked document lists using weighted Reciprocal Rank Fusion (RRF).

        Final score for each doc_id:
          beta * (1 / (rrf_k + rank_semantic)) + (1 - beta) * (1 / (rrf_k + rank_lexical))
        for each list where the doc appears (primary = semantic/FAISS, secondary = BM25).
        """
        rrf_k = settings.rrf_k
        hybrid_beta = settings.hybrid_beta

        primary_ranks: dict[str, int] = {}
        secondary_ranks: dict[str, int] = {}
        docs_by_id: dict[str, Document] = {}
        first_seen_order: dict[str, int] = {}

        def _ingest(docs: list[Document], *, target_ranks: dict[str, int]) -> None:
            for rank, doc in enumerate(docs, start=1):
                doc_id = doc.metadata.get("doc_id")
                if not doc_id:
                    continue

                # Keep the earliest (best) rank only.
                target_ranks.setdefault(doc_id, rank)

                # Preserve a deterministic representative doc for the fused output.
                if doc_id not in docs_by_id:
                    docs_by_id[doc_id] = doc
                    first_seen_order[doc_id] = len(first_seen_order)

        _ingest(primary_docs, target_ranks=primary_ranks)
        _ingest(secondary_docs, target_ranks=secondary_ranks)

        fused: list[tuple[str, float, int, int]] = []
        all_doc_ids = set(docs_by_id.keys())

        for doc_id in all_doc_ids:
            score = 0.0
            min_rank = 10**18

            if doc_id in primary_ranks:
                rank = primary_ranks[doc_id]
                score += hybrid_beta * (1.0 / (rrf_k + rank))
                min_rank = min(min_rank, rank)

            if doc_id in secondary_ranks:
                rank = secondary_ranks[doc_id]
                score += (1.0 - hybrid_beta) * (1.0 / (rrf_k + rank))
                min_rank = min(min_rank, rank)

            fused.append((doc_id, score, min_rank, first_seen_order[doc_id]))

        # Sort by fused score desc, then by best (lowest) rank asc, then by first-seen order asc.
        fused.sort(key=lambda item: (-item[1], item[2], item[3]))

        limit = max_docs if max_docs is not None else len(fused)
        fused_doc_ids = [doc_id for doc_id, _, _, _ in fused[:limit]]
        return [docs_by_id[doc_id] for doc_id in fused_doc_ids]

    def _retrieve_summary_docs(
        self,
        *,
        settings: RetrievalSettings,
        project: Project,
        retrieval_query: str,
        enable_hybrid_retrieval: bool,
        filters: RetrievalFilters | None = None,
        similarity_search_k: int | None = None,
    ) -> dict:
        k_vec = (
            int(similarity_search_k)
            if similarity_search_k is not None
            else int(settings.similarity_search_k)
        )
        k_vec = max(1, k_vec)
        fetch_k = vector_search_fetch_k(base_k=k_vec, filters=filters)
        vector_summary_docs = self.vectorstore_service.similarity_search(
            project,
            retrieval_query,
            k=fetch_k,
        )
        if filters is not None and not filters.is_empty():
            vector_summary_docs = filter_summary_documents_by_filters(
                vector_summary_docs,
                filters,
            )[:k_vec]

        bm25_summary_docs: list[Document] = []

        if enable_hybrid_retrieval:
            project_assets = self.docstore_service.list_assets_for_project(
                user_id=project.user_id,
                project_id=project.project_id,
            )

            bm25_summary_docs = self.hybrid_retrieval_service.lexical_search(
                query=retrieval_query,
                assets=project_assets,
                k=settings.bm25_search_k,
                filters=filters,
                k1=settings.bm25_k1,
                b=settings.bm25_b,
                epsilon=settings.bm25_epsilon,
            )

        merged_limit = k_vec
        if enable_hybrid_retrieval:
            merged_limit += int(settings.hybrid_search_k)

        recalled_summary_docs = self._merge_summary_docs(
            settings=settings,
            primary_docs=vector_summary_docs,
            secondary_docs=bm25_summary_docs,
            max_docs=merged_limit,
        )

        return {
            "vector_summary_docs": vector_summary_docs,
            "bm25_summary_docs": bm25_summary_docs,
            "recalled_summary_docs": recalled_summary_docs,
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
    ) -> dict | None:
        pipeline_started = perf_counter()
        if chat_history is None:
            chat_history = []

        rss = self.retrieval_settings_service
        settings = rss.merge(rss.get_default(), retrieval_settings)
        if enable_query_rewrite_override is not None:
            settings = replace(settings, enable_query_rewrite=enable_query_rewrite_override)
        if enable_hybrid_retrieval_override is not None:
            settings = replace(settings, enable_hybrid_retrieval=enable_hybrid_retrieval_override)

        logger.debug(
            "Retrieval settings (project_id=%s): %s",
            project.project_id,
            settings.to_log_dict(),
        )

        enable_query_rewrite = settings.enable_query_rewrite
        enable_hybrid_retrieval = settings.enable_hybrid_retrieval

        t0 = perf_counter()
        rewritten_question = self._rewrite_question(
            question,
            chat_history,
            enable_query_rewrite=enable_query_rewrite,
            settings=settings,
        )
        query_rewrite_ms = (perf_counter() - t0) * 1000.0

        query_intent = self.query_intent_service.classify(rewritten_question)
        table_aware_qa_enabled = self.table_qa_service.is_table_query(
            query_intent=query_intent,
            question=rewritten_question,
        )

        use_adaptive_retrieval = enable_hybrid_retrieval_override is None
        if use_adaptive_retrieval:
            strategy = self.adaptive_retrieval_service.choose_strategy(
                settings=settings,
                intent=query_intent,
                rewritten_query=rewritten_question,
            )
            enable_hybrid_retrieval = strategy.use_hybrid
            similarity_search_k = strategy.k
        else:
            strategy = RetrievalStrategy(
                k=max(1, int(settings.similarity_search_k)),
                use_hybrid=bool(enable_hybrid_retrieval),
                apply_filters=True,
            )
            similarity_search_k = strategy.k

        filters_for_retrieval = (
            filters if filters is not None and not filters.is_empty() else None
        )

        t0 = perf_counter()
        retrieval_payload = self._retrieve_summary_docs(
            settings=settings,
            project=project,
            retrieval_query=rewritten_question,
            enable_hybrid_retrieval=enable_hybrid_retrieval,
            filters=filters_for_retrieval,
            similarity_search_k=similarity_search_k,
        )
        retrieval_ms = (perf_counter() - t0) * 1000.0

        vector_summary_docs = retrieval_payload["vector_summary_docs"]
        bm25_summary_docs = retrieval_payload["bm25_summary_docs"]
        recalled_summary_docs = retrieval_payload["recalled_summary_docs"]

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
        section_expansion = {
            "enabled": bool(settings.enable_section_expansion),
            "applied": expansion.applied,
            "section_expansion_count": expansion.section_expansion_count,
            "expanded_assets_count": expansion.expanded_assets_count,
            "recall_pool_size": len(recalled_raw_assets),
        }

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
        context_compression = {
            "enabled": bool(settings.enable_contextual_compression),
            "applied": compression_applied and bool(settings.enable_contextual_compression),
            "chars_before": chars_before,
            "chars_after": chars_after,
            "ratio": round(ratio, 4),
        }

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

        payload = {
            "question": question,
            "rewritten_question": rewritten_question,
            "query_intent": query_intent.value,
            "table_aware_qa_enabled": table_aware_qa_enabled,
            "chat_history": chat_history,
            "retrieval_mode": retrieval_mode,
            "query_rewrite_enabled": enable_query_rewrite,
            "hybrid_retrieval_enabled": enable_hybrid_retrieval,
            "adaptive_retrieval_enabled": use_adaptive_retrieval,
            "retrieval_strategy": strategy.to_dict(),
            "retrieval_filters": (
                filters_for_retrieval.to_dict()
                if filters_for_retrieval is not None
                else None
            ),
            "vector_summary_docs": vector_summary_docs,
            "bm25_summary_docs": bm25_summary_docs,
            "recalled_summary_docs": recalled_summary_docs,
            "recalled_doc_ids": recalled_doc_ids,
            "recalled_raw_assets": recalled_raw_assets,
            "pre_rerank_raw_assets": pre_rerank_raw_assets,
            "section_expansion": section_expansion,
            "selected_summary_docs": selected_summary_docs,
            "selected_doc_ids": selected_doc_ids,
            "reranked_raw_assets": reranked_raw_assets,
            "prompt_context_assets": prompt_context_assets,
            "context_compression": context_compression,
            "source_references": source_references,
            "image_context_enriched": image_context_enriched,
            "multimodal_analysis": multimodal_analysis,
            "multimodal_orchestration_hint": multimodal_orchestration_hint,
            "raw_context": raw_context,
            "prompt": prompt,
            "confidence": confidence,
            "latency": latency_dict,
            "latency_ms": total_pipeline_ms,
        }

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
                    "context_compression_chars_before": context_compression["chars_before"],
                    "context_compression_chars_after": context_compression["chars_after"],
                    "context_compression_ratio": context_compression["ratio"],
                    "section_expansion_count": section_expansion["section_expansion_count"],
                    "expanded_assets_count": section_expansion["expanded_assets_count"],
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
    ) -> dict | None:
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

    def generate_answer_from_pipeline(self, *, project: Project, pipeline: dict) -> str:
        """
        Generate the final answer from an already-prepared pipeline payload.

        This keeps dataset evaluation and interactive chat aligned on the exact
        same answer generation logic without duplicating LLM invocation code.
        """
        try:
            response = LLM.invoke(pipeline["prompt"])
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
        )

        if pipeline is None:
            return None

        gen_started = perf_counter()
        answer = self.generate_answer_from_pipeline(project=project, pipeline=pipeline)
        answer_generation_ms = (perf_counter() - gen_started) * 1000.0
        total_ms = (perf_counter() - ask_started) * 1000.0
        full_latency = merge_with_answer_stage(
            pipeline.get("latency"),
            answer_generation_ms=answer_generation_ms,
            total_ms=total_ms,
        )
        full_latency_dict = full_latency.to_dict()
        pipeline["latency"] = full_latency_dict
        pipeline["latency_ms"] = total_ms

        if defer_log:
            self._safe_log_query(
                {
                    "question": question,
                    "rewritten_query": pipeline.get("rewritten_question"),
                    "project_id": project.project_id,
                    "user_id": project.user_id,
                    "selected_doc_ids": pipeline.get("selected_doc_ids"),
                    "retrieved_doc_ids": pipeline.get("recalled_doc_ids"),
                    "latency_ms": total_ms,
                    "confidence": pipeline.get("confidence"),
                    "answer": answer,
                    "hybrid_retrieval_enabled": pipeline.get("hybrid_retrieval_enabled"),
                    "retrieval_mode": pipeline.get("retrieval_mode"),
                    "query_intent": pipeline.get("query_intent"),
                    "table_aware_qa_enabled": pipeline.get("table_aware_qa_enabled"),
                    "retrieval_strategy": pipeline.get("retrieval_strategy"),
                    "context_compression_chars_before": (
                        (pipeline.get("context_compression") or {}).get("chars_before")
                    ),
                    "context_compression_chars_after": (
                        (pipeline.get("context_compression") or {}).get("chars_after")
                    ),
                    "context_compression_ratio": (pipeline.get("context_compression") or {}).get("ratio"),
                    "section_expansion_count": (pipeline.get("section_expansion") or {}).get(
                        "section_expansion_count"
                    ),
                    "expanded_assets_count": (pipeline.get("section_expansion") or {}).get(
                        "expanded_assets_count"
                    ),
                    **self._latency_fields_for_query_log(full_latency),
                }
            )

        return RAGResponse(
            question=question,
            answer=answer,
            source_documents=pipeline["selected_summary_docs"],
            raw_assets=pipeline["reranked_raw_assets"],
            citations=pipeline["source_references"],
            confidence=pipeline["confidence"],
            latency=full_latency_dict,
        )
