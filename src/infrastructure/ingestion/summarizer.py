from src.core.config import LLM


MAX_SUMMARY_INPUT_CHARS = 4000


class ElementSummarizer:
    def summarize(self, content_type: str, raw_content: str) -> str:
        if content_type == "image":
            return (
                "Visual asset extracted from the uploaded document. "
                "This asset may contain charts, diagrams, screenshots, figures, "
                "or other page-level visual information."
            )

        trimmed_content = (raw_content or "").strip()[:MAX_SUMMARY_INPUT_CHARS]

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
            prompt = f"""
You are generating a retrieval summary for a table.

Instructions:
- Describe what the table contains
- Mention key entities, comparisons, and important values if visible
- Make it dense and searchable
- Use 3 to 5 sentences max

TABLE:
{trimmed_content}
"""
        else:
            prompt = f"""
Generate a dense retrieval summary for the following content:

{trimmed_content}
"""

        response = LLM.invoke(prompt)
        return getattr(response, "content", str(response)).strip()
