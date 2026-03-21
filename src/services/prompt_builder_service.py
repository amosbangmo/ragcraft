from src.domain.source_citation import SourceCitation


class PromptBuilderService:
    def __init__(
        self,
        *,
        max_text_chars_per_asset: int,
        max_table_chars_per_asset: int,
    ):
        self.max_text_chars_per_asset = max_text_chars_per_asset
        self.max_table_chars_per_asset = max_table_chars_per_asset

    def build_raw_context(
        self,
        *,
        raw_assets: list[dict],
        citations: list[SourceCitation],
    ) -> str:
        """``raw_assets`` may be context-compressed upstream before this call."""
        blocks = [
            self._format_raw_asset_for_prompt(asset=asset, citation=citation)
            for asset, citation in zip(raw_assets, citations)
        ]
        return "\n\n".join(blocks)

    def build_prompt(
        self,
        *,
        question: str,
        chat_history: list[str],
        raw_context: str,
        table_aware_instruction: str | None = None,
    ) -> str:
        history_text = "\n".join(chat_history) if chat_history else "No prior chat history."

        table_block = ""
        if table_aware_instruction and table_aware_instruction.strip():
            table_block = f"\n{table_aware_instruction.strip()}\n"

        return f"""
You are an AI assistant answering questions using only the provided raw multimodal context.

Chat history:
{history_text}

Question:
{question}

Raw multimodal context:
{raw_context}
{table_block}
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
""".strip()

    def _format_raw_asset_for_prompt(self, *, asset: dict, citation: SourceCitation) -> str:
        content_type = asset.get("content_type", "unknown")
        source_file = asset.get("source_file", "unknown")
        raw_content = asset.get("raw_content", "") or ""
        metadata = asset.get("metadata", {}) or {}
        summary = asset.get("summary", "") or ""
        doc_id = asset.get("doc_id", "?")
        citation_label = citation.prompt_label

        if content_type == "text":
            trimmed = raw_content[: self.max_text_chars_per_asset]
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
{raw_content[: self.max_table_chars_per_asset]}

Raw table text:
{table_text[: self.max_table_chars_per_asset]}
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
