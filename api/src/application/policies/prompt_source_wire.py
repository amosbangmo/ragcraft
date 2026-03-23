"""Serialize :class:`~domain.prompt_source.PromptSource` for API / UI payloads."""

from __future__ import annotations

from domain.rag.prompt_source import PromptSource


def prompt_source_to_wire_dict(prompt_source: PromptSource) -> dict:
    rerank_score = prompt_source.metadata.get("rerank_score") if prompt_source.metadata else None

    return {
        "source_number": prompt_source.source_number,
        "doc_id": prompt_source.doc_id,
        "source_file": prompt_source.source_file,
        "content_type": prompt_source.content_type,
        "page_label": prompt_source.page_label,
        "locator_label": prompt_source.locator_label,
        "display_label": prompt_source.display_label,
        "inline_label": prompt_source.prompt_label,
        "metadata": prompt_source.metadata,
        "rerank_score": rerank_score,
    }
