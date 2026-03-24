"""Tests for frontend wire parsing and HTTP error mapping (canonical API client contract)."""

from __future__ import annotations

import httpx
import pytest

from infrastructure.config.exceptions import VectorStoreError
from services.api_client import HttpBackendClient
from services.backend.http_error_map import raise_for_api_response
from services.backend.http_payloads import (
    effective_retrieval_view_from_api_dict,
    rag_answer_from_ask_api_dict,
)
from services.contract.api_contract_models import IngestDocumentPayload, IngestionDiagnosticsPayload


def test_rag_answer_from_ask_api_dict_no_pipeline() -> None:
    assert rag_answer_from_ask_api_dict({"status": "no_pipeline"}) is None


def test_rag_answer_from_ask_api_dict_answered() -> None:
    r = rag_answer_from_ask_api_dict(
        {
            "status": "answered",
            "question": "q",
            "answer": "a",
            "source_documents": [{"id": 1}],
            "raw_assets": [],
            "prompt_sources": [],
            "confidence": 0.5,
            "latency": {"total_ms": 12.0},
        }
    )
    assert r is not None
    assert r.question == "q"
    assert r.answer == "a"
    assert r.confidence == 0.5
    assert r.latency == {"total_ms": 12.0}
    assert len(r.source_documents) == 1


def test_effective_retrieval_view_from_api_dict_minimal() -> None:
    data = {
        "preferences": {
            "user_id": "u",
            "project_id": "p",
            "retrieval_preset": "balanced",
            "retrieval_advanced": False,
            "enable_query_rewrite": True,
            "enable_hybrid_retrieval": True,
        },
        "effective_retrieval": {"enable_query_rewrite": False},
    }
    view = effective_retrieval_view_from_api_dict(data)
    assert view.preferences.user_id == "u"
    assert view.preferences.project_id == "p"
    assert view.effective_retrieval.enable_query_rewrite is False


def test_raise_for_api_response_maps_llm_error_type() -> None:
    from infrastructure.config.exceptions import LLMServiceError

    with pytest.raises(LLMServiceError) as ei:
        raise_for_api_response(
            503,
            {"error_type": "LLMServiceError", "message": "model down"},
            "fallback",
        )
    assert "model down" in str(ei.value)


def test_ingest_payload_format_messages_match_streamlit_copy() -> None:
    p = IngestDocumentPayload(
        raw_assets=[{"content_type": "text"}],
        replacement_info={"deleted_assets": 1, "deleted_vectors": 2},
        diagnostics=IngestionDiagnosticsPayload(),
    )
    assert "replaced previous ingestion" in p.format_ingestion_success_message("f.pdf")
    assert "reindexed successfully" in p.format_reindex_success_message("f.pdf")


def test_http_backend_client_surfaces_vector_store_error_envelope() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/chat/ask":
            return httpx.Response(
                503,
                json={
                    "error_type": "VectorStoreError",
                    "message": "index missing",
                },
            )
        return httpx.Response(404, json={"detail": "no"})

    client = HttpBackendClient(
        base_url="http://test.local",
        transport=httpx.MockTransport(handler),
        access_token_supplier=lambda: "tok",
    )
    try:
        with pytest.raises(VectorStoreError):
            client.ask_question("u", "p", "q")
    finally:
        client.close()


def test_api_client_facade_reexports_backend_entrypoints() -> None:
    import services.api_client as ac

    assert hasattr(ac, "HttpBackendClient")
    assert hasattr(ac, "get_backend_client")
    assert hasattr(ac, "RAGAnswer")
