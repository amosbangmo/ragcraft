from langchain_core.documents import Document

from src.core.config import LLM, RETRIEVAL_CONFIG
from src.core.exceptions import LLMServiceError
from src.domain.project import Project
from src.domain.rag_response import RAGResponse
from src.domain.source_citation import SourceCitation
from src.services.docstore_service import DocStoreService
from src.services.evaluation_service import EvaluationService
from src.services.reranking_service import RerankingService
from src.services.source_citation_service import SourceCitationService
from src.services.vectorstore_service import VectorStoreService


class RAGService:
    """
    Multi-step RAG service:
    1. large recall retrieval from FAISS over summary documents
    2. raw asset rehydration from SQLite using doc_id
    3. strict reranking over the rehydrated raw assets
    4. final prompt built only from the top reranked assets
    """

    def __init__(
        self,
        vectorstore_service: VectorStoreService,
        evaluation_service: EvaluationService,
        docstore_service: DocStoreService,
        reranking_service: RerankingService,
    ):
        self.vectorstore_service = vectorstore_service
        self.evaluation_service = evaluation_service
        self.docstore_service = docstore_service
        self.reranking_service = reranking_service
        self.source_citation_service = SourceCitationService()
        self.config = RETRIEVAL_CONFIG

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

    def _format_raw_asset_for_prompt(self, asset: dict, citation: SourceCitation) -> str:
        content_type = asset.get("content_type", "unknown")
        source_file = asset.get("source_file", "unknown")
        raw_content = asset.get("raw_content", "") or ""
        metadata = asset.get("metadata", {}) or {}
        summary = asset.get("summary", "") or ""
        doc_id = asset.get("doc_id", "?")
        citation_label = citation.prompt_label

        if content_type == "text":
            trimmed = raw_content[: self.config.max_text_chars_per_asset]
            return f"""Asset {citation.source_number}
Citation: {citation_label}
Type: text
Doc ID: {doc_id}
Source file: {source_file}
Metadata: {metadata}

Raw text:
{trimmed}
"""

        if content_type == "table":
            table_title = metadata.get("table_title")
            table_text = metadata.get("table_text") or ""

            return f"""Asset {citation.source_number}
Citation: {citation_label}
Type: table
Doc ID: {doc_id}
Source file: {source_file}
Metadata: {metadata}

Table title:
{table_title}

Raw table HTML:
{raw_content[: self.config.max_table_chars_per_asset]}

Raw table text:
{table_text[: self.config.max_table_chars_per_asset]}
"""

        if content_type == "image":
            image_context = {
                "page_number": metadata.get("page_number"),
                "page_start": metadata.get("page_start"),
                "page_end": metadata.get("page_end"),
                "image_index": metadata.get("image_index"),
                "image_mime_type": metadata.get("image_mime_type"),
                "element_category": metadata.get("element_category"),
                "embedded_path": metadata.get("embedded_path"),
                "image_title": metadata.get("image_title"),
                "rerank_score": metadata.get("rerank_score"),
            }

            return f"""Asset {citation.source_number}
Citation: {citation_label}
Type: image
Doc ID: {doc_id}
Source file: {source_file}
Metadata: {image_context}

Image retrieval summary:
{summary}

Raw image:
[Binary image asset stored in SQLite as base64 and intentionally omitted from this final prompt.]
"""

        trimmed = raw_content[:2000]
        return f"""Asset {citation.source_number}
Citation: {citation_label}
Type: {content_type}
Doc ID: {doc_id}
Source file: {source_file}
Metadata: {metadata}

Raw content:
{trimmed}
"""

    def _build_raw_context(self, raw_assets: list[dict], citations: list[SourceCitation]) -> str:
        blocks = [
            self._format_raw_asset_for_prompt(asset, citation)
            for asset, citation in zip(raw_assets, citations)
        ]
        return "\n\n".join(blocks)

    def _build_prompt(
        self,
        *,
        question: str,
        chat_history: list[str],
        raw_context: str,
    ) -> str:
        history_text = "\n".join(chat_history) if chat_history else "No prior chat history."

        return f"""
You are an AI assistant answering questions using only the provided raw multimodal context.

Chat history:
{history_text}

Question:
{question}

Raw multimodal context:
{raw_context}

Instructions:
- Use only the provided raw context.
- Retrieval happened in two stages:
  1. large recall retrieval over summary documents
  2. strict reranking over rehydrated raw assets
- Only the final reranked assets are included in the context.
- If the answer is not supported by the raw context, say you don't know.
- Be precise and concise.
- Every factual claim grounded in a source should include its citation label.
- Use the exact citation labels provided in each asset block.
- Citations must be inline, for example:
  - [Source 1]
  - [Source 2][Tableau: Table 2]
  - [Source 3][Figure: Attention map]
- When useful, mention whether the evidence came from text, table, or image assets.
- For image assets, rely only on their provided metadata and image retrieval summary; do not invent unseen visual details.
- Never invent document content that is not explicitly present in the raw context.
"""

    def _run_pipeline(self, project: Project, question: str, chat_history=None) -> dict | None:
        if chat_history is None:
            chat_history = []

        recalled_summary_docs = self.vectorstore_service.similarity_search(
            project,
            question,
            k=self.config.retrieval_k,
        )

        if not recalled_summary_docs:
            return None

        recalled_doc_ids = self._deduplicate_doc_ids(recalled_summary_docs)
        if not recalled_doc_ids:
            return None

        recalled_raw_assets = self.docstore_service.get_assets_by_doc_ids(recalled_doc_ids)
        if not recalled_raw_assets:
            return None

        reranked_raw_assets = self.reranking_service.rerank(
            query=question,
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

        raw_context = self._build_raw_context(reranked_raw_assets, citation_objects)
        prompt = self._build_prompt(
            question=question,
            chat_history=chat_history,
            raw_context=raw_context,
        )

        confidence_docs = selected_summary_docs if selected_summary_docs else recalled_summary_docs
        confidence = self.evaluation_service.compute_confidence(confidence_docs)

        return {
            "question": question,
            "chat_history": chat_history,
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

    def inspect_pipeline(self, project: Project, question: str, chat_history=None) -> dict | None:
        return self._run_pipeline(project, question, chat_history)

    def ask(self, project: Project, question: str, chat_history=None) -> RAGResponse | None:
        pipeline = self._run_pipeline(project, question, chat_history)

        if pipeline is None:
            return None

        try:
            response = LLM.invoke(pipeline["prompt"])
        except Exception as exc:
            raise LLMServiceError(
                f"Failed to generate answer for project '{project.project_id}': {exc}",
                user_message="The language model failed while generating the answer.",
            ) from exc

        answer = getattr(response, "content", str(response)).strip()

        return RAGResponse(
            question=question,
            answer=answer,
            source_documents=pipeline["selected_summary_docs"],
            raw_assets=pipeline["reranked_raw_assets"],
            citations=pipeline["source_references"],
            confidence=pipeline["confidence"],
        )
