from time import perf_counter
from typing import Any

from src.core.config import LLM
from src.core.exceptions import LLMServiceError
from src.domain.pipeline_latency import PipelineLatency, merge_with_answer_stage
from src.domain.pipeline_payloads import PipelineBuildResult
from src.domain.project import Project
from src.domain.rag_response import RAGResponse
from src.domain.retrieval_filters import RetrievalFilters
from src.services.docstore_service import DocStoreService
from src.services.evaluation_service import EvaluationService
from src.services.pipeline_assembly_service import PipelineAssemblyService
from src.services.query_log_service import QueryLogService
from src.services.reranking_service import RerankingService
from src.services.retrieval_settings_service import RetrievalSettingsService
from src.services.summary_recall_service import SummaryRecallService
from src.services.table_qa_service import TableQAService
from src.services.vectorstore_service import VectorStoreService


class RAGService:
    """
    Multi-step RAG service:
    1. optional query rewriting
    2. hybrid recall retrieval (FAISS + BM25 summaries)
    3. pipeline assembly: raw asset rehydration, section expansion, reranking,
       optional contextual compression, citations, and prompt construction
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
        self.pipeline_assembly_service = PipelineAssemblyService(
            docstore_service=docstore_service,
            reranking_service=reranking_service,
            table_qa_service=self.table_qa_service,
        )
        self.query_log_service = query_log_service

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

        payload = self.pipeline_assembly_service.build(
            project=project,
            question=question,
            chat_history=chat_history,
            recall=bundle,
            pipeline_started_monotonic=pipeline_started,
        )

        if payload is None:
            return None

        latency = PipelineLatency.from_dict(payload.latency)

        if self.query_log_service is not None and not defer_query_log:
            section_expansion = payload.section_expansion
            context_compression = payload.context_compression
            self._safe_log_query(
                {
                    "question": question,
                    "rewritten_query": payload.rewritten_question,
                    "project_id": project.project_id,
                    "user_id": project.user_id,
                    "selected_doc_ids": payload.selected_doc_ids,
                    "retrieved_doc_ids": payload.recalled_doc_ids,
                    "latency_ms": latency.total_ms,
                    "confidence": payload.confidence,
                    "hybrid_retrieval_enabled": payload.hybrid_retrieval_enabled,
                    "retrieval_mode": payload.retrieval_mode,
                    "query_intent": payload.query_intent.value,
                    "table_aware_qa_enabled": payload.table_aware_qa_enabled,
                    "retrieval_strategy": payload.retrieval_strategy.to_dict(),
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
            full_lat = PipelineLatency.from_dict(full_latency_dict)
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
                    **self._latency_fields_for_query_log(full_lat),
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
