from src.core.config import INGESTION_CONFIG, LLM


class ElementSummarizer:
    def summarize(
        self,
        content_type: str,
        raw_content: str,
        metadata: dict | None = None,
    ) -> str:
        metadata = metadata or {}
        max_summary_input_chars = INGESTION_CONFIG.summary_max_input_chars

        if content_type == "image":
            prompt = f"""
You are generating a retrieval summary for an extracted image block from a document.

Known metadata:
- source_file: {metadata.get("source_file")}
- page_number: {metadata.get("page_number")}
- element_category: {metadata.get("element_category")}
- image_mime_type: {metadata.get("image_mime_type")}
- embedded_path: {metadata.get("embedded_path")}
- image_index: {metadata.get("image_index")}
- image_title: {metadata.get("image_title")}

Instructions:
- Produce a concise retrieval-oriented description
- This is a true extracted image asset from the document
- Mention its title if available
- Mention whether it is likely an embedded figure, chart, diagram, screenshot, photo, or illustration
- Do not invent specific visible details
- Use 2 to 4 sentences max
"""
            response = LLM.invoke(prompt)
            return getattr(response, "content", str(response)).strip()

        trimmed_content = (raw_content or "").strip()[:max_summary_input_chars]

        if not trimmed_content:
            return f"Empty or non-textual {content_type} asset."

        if content_type == "text":
            prompt = f"""
You are generating a retrieval summary for a text chunk.

Instructions:
- Keep the summary faithful to the source
- Preserve names, dates, numbers, entities, and technical terms
- Make it dense and searchable
- Use 3 to 5 sentences max

TEXT:
{trimmed_content}
"""
        elif content_type == "table":
            table_title = metadata.get("table_title")
            table_text = metadata.get("table_text") or ""

            prompt = f"""
You are generating a retrieval summary for a table.

Instructions:
- Describe what the table contains
- Mention its title if available
- Mention key entities, comparisons, and important values if visible
- Make it dense and searchable
- Use 3 to 5 sentences max

TABLE TITLE:
{table_title}

TABLE HTML:
{trimmed_content[:3000]}

TABLE TEXT:
{table_text[:3000]}
"""
        else:
            prompt = f"""
Generate a dense retrieval summary for the following content:

{trimmed_content}
"""

        response = LLM.invoke(prompt)
        return getattr(response, "content", str(response)).strip()
