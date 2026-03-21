"""Lightweight modality detection and prompt hints for multimodal RAG answers."""

_TEXT = "text"
_TABLE = "table"
_IMAGE = "image"


class MultimodalOrchestrationService:
    """
    Inspects prompt-facing assets and produces optional orchestration text for the LLM.
    Single-modality contexts return an empty hint so behavior stays unchanged.
    """

    def analyze(self, assets: list[dict]) -> dict:
        has_text = False
        has_table = False
        has_image = False
        for asset in assets:
            ct = str(asset.get("content_type") or "").strip().lower()
            if ct == _TEXT:
                has_text = True
            elif ct == _TABLE:
                has_table = True
            elif ct == _IMAGE:
                has_image = True
        modality_count = sum((has_text, has_table, has_image))
        return {
            "has_text": has_text,
            "has_table": has_table,
            "has_image": has_image,
            "modality_count": modality_count,
        }

    def build_prompt_hint(self, analysis: dict) -> str:
        if int(analysis.get("modality_count") or 0) < 2:
            return ""

        has_text = bool(analysis.get("has_text"))
        has_table = bool(analysis.get("has_table"))
        has_image = bool(analysis.get("has_image"))

        parts: list[str] = []

        if has_text and has_table and has_image:
            parts.append(
                "Combine textual explanations, precise values from tables, and image-oriented context "
                "(titles, captions, same-page text, retrieval summaries) when answering. Cite each modality you use."
            )
        elif has_text and has_table:
            parts.append(
                "Use the table to extract precise values and comparisons; use the text to explain, contextualize, "
                "and interpret those values. Cite both."
            )
        elif has_table and has_image:
            parts.append(
                "Use the table for exact values and structured facts; use the image blocks for contextual "
                "understanding (what is referenced, where it sits in the document). Cite both."
            )
        elif has_text and has_image:
            parts.append(
                "Use text passages for narrative and definitions; use image metadata, surrounding text, and the "
                "image retrieval summary for figure-oriented grounding. Cite both."
            )

        parts.append(
            "Structure your answer clearly: open with a short direct explanation; use bullet points for key "
            "table-derived facts when a table is in context; explicitly label image-grounded claims (metadata / "
            "surrounding text / retrieval summary only). Separate explanation from supporting evidence when that "
            "improves readability."
        )

        return "\n".join(parts)
