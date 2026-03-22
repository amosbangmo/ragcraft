from __future__ import annotations

from langchain_core.documents import Document

from src.infrastructure.web.json_normalization import jsonify_value


def test_jsonify_document_to_page_content_metadata_shape() -> None:
    doc = Document(page_content="hello", metadata={"doc_id": "d1", "n": 2})
    out = jsonify_value(doc)
    assert out == {
        "page_content": "hello",
        "metadata": {"doc_id": "d1", "n": 2},
    }


def test_jsonify_nested_list_and_dict() -> None:
    doc = Document(page_content="x", metadata={})
    assert jsonify_value({"docs": [doc], "k": 1}) == {
        "docs": [{"page_content": "x", "metadata": {}}],
        "k": 1,
    }


def test_jsonify_object_with_to_dict() -> None:
    class Box:
        def to_dict(self):
            return {"inner": Document(page_content="z", metadata={"a": 1})}

    out = jsonify_value(Box())
    assert out == {"inner": {"page_content": "z", "metadata": {"a": 1}}}
