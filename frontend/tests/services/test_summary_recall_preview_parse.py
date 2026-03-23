from __future__ import annotations

from services.http_payloads import summary_recall_preview_from_api_dict


def test_summary_recall_preview_from_api_dict_maps_docs() -> None:
    raw = {
        "rewritten_question": "rq",
        "recalled_summary_docs": [{"page_content": "c", "metadata": {"doc_id": "1"}}],
        "vector_summary_docs": [],
        "bm25_summary_docs": [],
        "retrieval_mode": "hybrid",
        "query_rewrite_enabled": True,
        "hybrid_retrieval_enabled": True,
        "use_adaptive_retrieval": False,
    }
    p = summary_recall_preview_from_api_dict(raw)
    assert p.rewritten_question == "rq"
    assert len(p.recalled_summary_docs) == 1
    assert p.recalled_summary_docs[0].page_content == "c"
    assert p.recalled_summary_docs[0].metadata["doc_id"] == "1"
    assert p.retrieval_mode == "hybrid"
