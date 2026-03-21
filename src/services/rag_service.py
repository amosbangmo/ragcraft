from time import perf_counter

from langchain_core.documents import Document

from src.core.config import LLM, RETRIEVAL_CONFIG
from src.core.exceptions import LLMServiceError
from src.domain.project import Project
from src.domain.rag_response import RAGResponse
from src.domain.source_citation import SourceCitation
from src.services.confidence_service import ConfidenceService
from src.services.docstore_service import DocStoreService
from src.services.evaluation_service import EvaluationService
from src.services.hybrid_retrieval_service import HybridRetrievalService
from src.services.prompt_builder_service import PromptBuilderService
from src.services.query_log_service import QueryLogService
from src.services.query_rewrite_service import QueryRewriteService
from src.services.reranking_service import RerankingService
from src.services.source_citation_service import SourceCitationService
from src.services.vectorstore_service import VectorStoreService


class RAGService:
    """
    Multi-step RAG service:
    1. optional query rewriting
    2. hybrid recall retrieval (FAISS + BM25 summaries)
    3. raw asset rehydration from SQLite using doc_id
    4. strict reranking over the rehydrated raw assets
    5. final prompt built only from the top reranked assets
    """

    def __init__(
        self,
        vectorstore_service: VectorStoreService,
        evaluation_service: EvaluationService,
        docstore_service: DocStoreService,
        reranking_service: RerankingService,
        query_log_service: QueryLogService | None = None,
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
        self.config = RETRIEVAL_CONFIG
        self.query_log_service = query_log_service

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
    ) -> str:
        if not enable_query_rewrite:
            return question

        return self.query_rewrite_service.rewrite(
            question=question,
            chat_history=chat_history,
        )

    def _merge_summary_docs(
        self,
        *,
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
        rrf_k = self.config.rrf_k
        hybrid_beta = self.config.hybrid_beta

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
        project: Project,
        retrieval_query: str,
        enable_hybrid_retrieval: bool,
    ) -> dict:
        vector_summary_docs = self.vectorstore_service.similarity_search(
            project,
            retrieval_query,
            k=self.config.similarity_search_k,
        )

        bm25_summary_docs: list[Document] = []

        if enable_hybrid_retrieval:
            project_assets = self.docstore_service.list_assets_for_project(
                user_id=project.user_id,
                project_id=project.project_id,
            )

            bm25_summary_docs = self.hybrid_retrieval_service.lexical_search(
                query=retrieval_query,
                assets=project_assets,
                k=self.config.bm25_search_k,
            )

        merged_limit = self.config.similarity_search_k
        if enable_hybrid_retrieval:
            merged_limit += self.config.hybrid_search_k

        recalled_summary_docs = self._merge_summary_docs(
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
    ) -> dict | None:
        pipeline_started = perf_counter()
        if chat_history is None:
            chat_history = []

        enable_query_rewrite = (
            self.config.enable_query_rewrite
            if enable_query_rewrite_override is None
            else enable_query_rewrite_override
        )
        enable_hybrid_retrieval = (
            self.config.enable_hybrid_retrieval
            if enable_hybrid_retrieval_override is None
            else enable_hybrid_retrieval_override
        )

        rewritten_question = self._rewrite_question(
            question,
            chat_history,
            enable_query_rewrite=enable_query_rewrite,
        )

        retrieval_payload = self._retrieve_summary_docs(
            project=project,
            retrieval_query=rewritten_question,
            enable_hybrid_retrieval=enable_hybrid_retrieval,
        )

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

        reranked_raw_assets = self.reranking_service.rerank(
            query=rewritten_question,
            raw_assets=recalled_raw_assets,
            top_k=self.config.max_prompt_assets,
        )

        if not reranked_raw_assets:
            return None

        selected_doc_ids = [asset.get("doc_id") for asset in reranked_raw_assets if asset.get("doc_id")]
        selected_summary_docs = self._select_summary_docs_by_doc_ids(
            recalled_summary_docs,
            selected_doc_ids,
        )

        citation_objects = self.source_citation_service.build_citations(reranked_raw_assets)
        source_references = [self._citation_to_dict(citation) for citation in citation_objects]

        raw_context = self.prompt_builder_service.build_raw_context(
            raw_assets=reranked_raw_assets,
            citations=citation_objects,
        )
        prompt = self.prompt_builder_service.build_prompt(
            question=question,
            chat_history=chat_history,
            raw_context=raw_context,
        )

        confidence = self.confidence_service.compute_confidence(
            reranked_raw_assets=reranked_raw_assets,
        )

        retrieval_mode = "faiss+bm25" if enable_hybrid_retrieval else "faiss"

        payload = {
            "question": question,
            "rewritten_question": rewritten_question,
            "chat_history": chat_history,
            "retrieval_mode": retrieval_mode,
            "query_rewrite_enabled": enable_query_rewrite,
            "hybrid_retrieval_enabled": enable_hybrid_retrieval,
            "vector_summary_docs": vector_summary_docs,
            "bm25_summary_docs": bm25_summary_docs,
            "recalled_summary_docs": recalled_summary_docs,
            "recalled_doc_ids": recalled_doc_ids,
            "recalled_raw_assets": recalled_raw_assets,
            "selected_summary_docs": selected_summary_docs,
            "selected_doc_ids": selected_doc_ids,
            "reranked_raw_assets": reranked_raw_assets,
            "source_references": source_references,
            "raw_context": raw_context,
            "prompt": prompt,
            "confidence": confidence,
        }

        if self.query_log_service is not None and not defer_query_log:
            pipeline_ms = (perf_counter() - pipeline_started) * 1000.0
            self._safe_log_query(
                {
                    "question": question,
                    "rewritten_query": rewritten_question,
                    "project_id": project.project_id,
                    "user_id": project.user_id,
                    "selected_doc_ids": selected_doc_ids,
                    "retrieved_doc_ids": recalled_doc_ids,
                    "latency_ms": pipeline_ms,
                    "confidence": confidence,
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
    ) -> dict | None:
        return self._run_pipeline(
            project,
            question,
            chat_history,
            enable_query_rewrite_override=enable_query_rewrite_override,
            enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
            defer_query_log=True,
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

    def ask(self, project: Project, question: str, chat_history=None) -> RAGResponse | None:
        ask_started = perf_counter()
        defer_log = self.query_log_service is not None
        pipeline = self._run_pipeline(
            project,
            question,
            chat_history,
            defer_query_log=defer_log,
        )

        if pipeline is None:
            return None

        answer = self.generate_answer_from_pipeline(project=project, pipeline=pipeline)
        total_ms = (perf_counter() - ask_started) * 1000.0

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
                }
            )

        return RAGResponse(
            question=question,
            answer=answer,
            source_documents=pipeline["selected_summary_docs"],
            raw_assets=pipeline["reranked_raw_assets"],
            citations=pipeline["source_references"],
            confidence=pipeline["confidence"],
        )
