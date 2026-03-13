from src.core.config import LLM
from src.domain.project import Project
from src.domain.rag_response import RAGResponse
from src.services.vectorstore_service import VectorStoreService
from src.services.evaluation_service import EvaluationService
from src.services.docstore_service import DocStoreService


MAX_RETRIEVED_SUMMARIES = 6
MAX_TEXT_CHARS_PER_ASSET = 4000
MAX_TABLE_CHARS_PER_ASSET = 4000
MAX_IMAGE_BASE64_PREVIEW_CHARS = 0  # do not inject base64 into final prompt


class RAGService:
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
        Kept for compatibility with existing cache plumbing.
        In PR2, the answering flow no longer relies on a retrieval chain object.
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

    def _format_raw_asset_for_prompt(self, asset: dict, index: int) -> str:
        content_type = asset.get("content_type", "unknown")
        source_file = asset.get("source_file", "unknown")
        raw_content = asset.get("raw_content", "") or ""
        metadata = asset.get("metadata", {}) or {}
        doc_id = asset.get("doc_id", "?")

        if content_type == "text":
            trimmed = raw_content[:MAX_TEXT_CHARS_PER_ASSET]
            return f"""Asset {index}
Type: text
Doc ID: {doc_id}
Source file: {source_file}
Metadata: {metadata}

Raw text:
{trimmed}
"""

        if content_type == "table":
            trimmed = raw_content[:MAX_TABLE_CHARS_PER_ASSET]
            return f"""Asset {index}
Type: table
Doc ID: {doc_id}
Source file: {source_file}
Metadata: {metadata}

Raw table:
{trimmed}
"""

        if content_type == "image":
            return f"""Asset {index}
Type: image
Doc ID: {doc_id}
Source file: {source_file}
Metadata: {metadata}

Raw image:
[Base64 asset stored in SQLite docstore and intentionally omitted from the final LLM prompt in PR2.]
"""

        trimmed = raw_content[:2000]
        return f"""Asset {index}
Type: {content_type}
Doc ID: {doc_id}
Source file: {source_file}
Metadata: {metadata}

Raw content:
{trimmed}
"""

    def _build_raw_context(self, raw_assets: list[dict]) -> str:
        blocks = [
            self._format_raw_asset_for_prompt(asset, index)
            for index, asset in enumerate(raw_assets, start=1)
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
- Do not rely on the summary retrieval layer; it was used only to find relevant assets.
- If the answer is not supported by the raw context, say you don't know.
- Be precise and concise.
- When useful, mention whether the evidence came from text, table, or image-derived assets.
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

        raw_context = self._build_raw_context(raw_assets)
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
            confidence=confidence,
        )
