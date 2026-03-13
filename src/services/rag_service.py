from src.core.config import LLM
from src.domain.project import Project
from src.domain.rag_response import RAGResponse
from src.services.vectorstore_service import VectorStoreService
from src.services.evaluation_service import EvaluationService
from src.services.docstore_service import DocStoreService


MAX_RETRIEVED_SUMMARIES = 6
MAX_TEXT_CHARS_PER_ASSET = 4000
MAX_TABLE_CHARS_PER_ASSET = 4000


class RAGService:
    """
    Multi-step RAG service:
    1. retrieve summary documents from FAISS
    2. rehydrate raw assets from SQLite using doc_id
    3. build a custom multimodal prompt
    4. answer from raw assets only
    """

    def __init__(
        self,
        vectorstore_service: VectorStoreService,
        evaluation_service: EvaluationService,
        docstore_service: DocStoreService,
    ):
        self.vectorstore_service = vectorstore_service
        self.evaluation_service = evaluation_service
        self.docstore_service = docstore_service

    def build_chain(self, project: Project):
        """
        Kept only for cache compatibility with the current app state design.
        Returns the project vector store instead of a LangChain retrieval chain.
        """
        return self.vectorstore_service.load(project)

    def _deduplicate_doc_ids(self, summary_docs: list) -> list[str]:
        seen = set()
        ordered_doc_ids: list[str] = []

        for doc in summary_docs:
            doc_id = doc.metadata.get("doc_id")
            if not doc_id or doc_id in seen:
                continue
            seen.add(doc_id)
            ordered_doc_ids.append(doc_id)

        return ordered_doc_ids

    def _build_source_reference(self, asset: dict, index: int) -> dict:
        content_type = asset.get("content_type", "unknown")
        source_file = asset.get("source_file", "unknown")
        metadata = asset.get("metadata", {}) or {}
        doc_id = asset.get("doc_id", "?")

        page_number = metadata.get("page_number")
        page_start = metadata.get("page_start")
        page_end = metadata.get("page_end")
        table_title = metadata.get("table_title")
        image_title = metadata.get("image_title")
        start_element_index = metadata.get("start_element_index")
        end_element_index = metadata.get("end_element_index")

        page_label = None
        if page_number:
            page_label = f"page {page_number}"
        elif page_start is not None and page_end is not None:
            if page_start == page_end:
                page_label = f"page {page_start}"
            else:
                page_label = f"pages {page_start}-{page_end}"
        elif page_start is not None:
            page_label = f"page {page_start}"

        structured_labels = [f"[Source {index}]"]

        locator_parts = []

        if content_type == "text":
            if start_element_index is not None and end_element_index is not None:
                if start_element_index == end_element_index:
                    locator_parts.append(f"Elements: {start_element_index}")
                else:
                    locator_parts.append(f"Elements: {start_element_index}-{end_element_index}")
        elif content_type == "table":
            if table_title:
                structured_labels.append(f"[Tableau: {table_title}]")
                locator_parts.append(f"Tableau: {table_title}")
            else:
                locator_parts.append("Tableau")
        elif content_type == "image":
            if image_title:
                structured_labels.append(f"[Figure: {image_title}]")
                locator_parts.append(f"Figure: {image_title}")
            else:
                locator_parts.append("Figure")

        if page_label:
            locator_parts.append(page_label)

        display_parts = [f"Source {index}", source_file]
        display_parts.extend(locator_parts)

        return {
            "source_number": index,
            "doc_id": doc_id,
            "source_file": source_file,
            "content_type": content_type,
            "page_label": page_label,
            "display_label": " — ".join(display_parts),
            "inline_label": "".join(structured_labels),
            "metadata": metadata,
        }

    def _format_raw_asset_for_prompt(self, asset: dict, source_reference: dict) -> str:
        content_type = asset.get("content_type", "unknown")
        source_file = asset.get("source_file", "unknown")
        raw_content = asset.get("raw_content", "") or ""
        metadata = asset.get("metadata", {}) or {}
        summary = asset.get("summary", "") or ""
        doc_id = asset.get("doc_id", "?")
        citation_label = source_reference["inline_label"]

        if content_type == "text":
            trimmed = raw_content[:MAX_TEXT_CHARS_PER_ASSET]
            return f"""Asset {source_reference["source_number"]}
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

            return f"""Asset {source_reference["source_number"]}
Citation: {citation_label}
Type: table
Doc ID: {doc_id}
Source file: {source_file}
Metadata: {metadata}

Table title:
{table_title}

Raw table HTML:
{raw_content[:3000]}

Raw table text:
{table_text[:3000]}
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
            }

            return f"""Asset {source_reference["source_number"]}
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
        return f"""Asset {source_reference["source_number"]}
Citation: {citation_label}
Type: {content_type}
Doc ID: {doc_id}
Source file: {source_file}
Metadata: {metadata}

Raw content:
{trimmed}
"""

    def _build_raw_context(self, raw_assets: list[dict], source_references: list[dict]) -> str:
        blocks = [
            self._format_raw_asset_for_prompt(asset, source_reference)
            for asset, source_reference in zip(raw_assets, source_references)
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
- The summary retrieval layer was used only to find relevant assets.
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

    def ask(self, project: Project, question: str, chat_history=None) -> RAGResponse | None:
        if chat_history is None:
            chat_history = []

        summary_docs = self.vectorstore_service.similarity_search(
            project,
            question,
            k=MAX_RETRIEVED_SUMMARIES,
        )

        if not summary_docs:
            return None

        doc_ids = self._deduplicate_doc_ids(summary_docs)
        if not doc_ids:
            return None

        raw_assets = self.docstore_service.get_assets_by_doc_ids(doc_ids)
        if not raw_assets:
            return None

        source_references = [
            self._build_source_reference(asset, index)
            for index, asset in enumerate(raw_assets, start=1)
        ]

        raw_context = self._build_raw_context(raw_assets, source_references)
        prompt = self._build_prompt(
            question=question,
            chat_history=chat_history,
            raw_context=raw_context,
        )

        response = LLM.invoke(prompt)
        answer = getattr(response, "content", str(response)).strip()

        confidence = self.evaluation_service.compute_confidence(summary_docs)

        return RAGResponse(
            question=question,
            answer=answer,
            source_documents=summary_docs,
            raw_assets=raw_assets,
            citations=source_references,
            confidence=confidence,
        )
