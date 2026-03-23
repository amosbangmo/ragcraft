"""Serialization of PromptSource for API-style dicts."""

from __future__ import annotations

from application.policies.prompt_source_wire import prompt_source_to_wire_dict
from domain.rag.prompt_source import PromptSource


def test_prompt_source_to_wire_dict_includes_rerank_score_from_metadata() -> None:
    ps = PromptSource(
        source_number=1,
        doc_id="d1",
        source_file="f.pdf",
        content_type="text",
        page_label="1",
        locator_label=None,
        display_label="f.pdf p1",
        prompt_label="[1]",
        metadata={"rerank_score": 0.42, "other": True},
    )

    wire = prompt_source_to_wire_dict(ps)

    assert wire["source_number"] == 1
    assert wire["doc_id"] == "d1"
    assert wire["inline_label"] == "[1]"
    assert wire["rerank_score"] == 0.42
    assert wire["metadata"]["other"] is True


def test_prompt_source_to_wire_dict_rerank_score_none_when_missing() -> None:
    ps = PromptSource(
        source_number=2,
        doc_id="d2",
        source_file="g.pdf",
        content_type="table",
        page_label=None,
        locator_label=None,
        display_label="g",
        prompt_label="[2]",
        metadata={},
    )

    wire = prompt_source_to_wire_dict(ps)

    assert wire["rerank_score"] is None
