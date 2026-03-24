from __future__ import annotations

import json

import httpx
import pytest

from services.contract.evaluation_wire_models import BenchmarkResult
from services.api_client import HttpBackendClient


def _bench_json() -> dict:
    return {
        "summary": {"rows": 0},
        "rows": [],
        "run_id": "run-1",
    }


def _make_mock_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        method = request.method
        if method == "GET" and path == "/projects":
            return httpx.Response(200, json={"projects": ["demo", "other"]})
        if method == "POST" and path == "/projects":
            body = json.loads(request.content.decode("utf-8")) if request.content else {}
            pid = body.get("project_id", "x")
            return httpx.Response(
                201,
                json={"project_id": pid},
            )
        if method == "GET" and path == "/projects/demo":
            return httpx.Response(200, json={"user_id": "u1", "project_id": "demo"})
        if method == "POST" and path == "/chat/ask":
            payload = json.loads(request.content.decode("utf-8"))
            assert "user_id" not in payload
            assert payload["question"] == "hi"
            return httpx.Response(
                200,
                json={
                    "status": "answered",
                    "question": "hi",
                    "answer": "hello",
                    "source_documents": [],
                    "raw_assets": [],
                    "prompt_sources": [],
                    "confidence": 0.9,
                    "latency": {"total_ms": 1.0},
                },
            )
        if method == "POST" and path == "/chat/pipeline/inspect":
            return httpx.Response(
                200,
                json={
                    "status": "ok",
                    "question": "q",
                    "pipeline": {"question": "q", "latency": {}},
                },
            )
        if method == "POST" and path == "/evaluation/dataset/run":
            return httpx.Response(200, json=_bench_json())
        return httpx.Response(404, json={"detail": "not found in mock"})

    return httpx.MockTransport(handler)


def test_http_backend_client_projects_list_and_create() -> None:
    client = HttpBackendClient(
        base_url="http://test.local",
        connect_timeout=1.0,
        read_timeout=5.0,
        transport=_make_mock_transport(),
        access_token_supplier=lambda: "test-bearer-token",
    )
    try:
        assert client.list_projects("u1") == ["demo", "other"]
        client.create_project("u1", "demo")
    finally:
        client.close()


def test_http_backend_client_chat_ask_returns_rag_response() -> None:
    client = HttpBackendClient(
        base_url="http://test.local",
        transport=_make_mock_transport(),
        access_token_supplier=lambda: "test-bearer-token",
    )
    try:
        r = client.ask_question("u1", "demo", "hi")
        assert r is not None
        assert r.answer == "hello"
        assert r.confidence == 0.9
    finally:
        client.close()


def test_http_backend_client_inspect_retrieval_returns_dict() -> None:
    client = HttpBackendClient(
        base_url="http://test.local",
        transport=_make_mock_transport(),
        access_token_supplier=lambda: "test-bearer-token",
    )
    try:
        pl = client.inspect_retrieval("u1", "demo", "q")
        assert isinstance(pl, dict)
        assert pl.get("question") == "q"
    finally:
        client.close()


def test_http_backend_client_evaluate_gold_qa_dataset() -> None:
    client = HttpBackendClient(
        base_url="http://test.local",
        transport=_make_mock_transport(),
        access_token_supplier=lambda: "test-bearer-token",
    )
    try:
        out = client.evaluate_gold_qa_dataset(
            user_id="u1",
            project_id="demo",
            enable_query_rewrite=False,
            enable_hybrid_retrieval=True,
        )
        assert isinstance(out, BenchmarkResult)
        assert out.run_id == "run-1"
    finally:
        client.close()


def test_frontend_backend_settings_split_timeouts(monkeypatch: pytest.MonkeyPatch) -> None:
    from services.config import settings as fg_settings

    fg_settings.load_frontend_backend_settings.cache_clear()
    monkeypatch.setenv("RAGCRAFT_API_BASE_URL", "http://127.0.0.1:9999")
    monkeypatch.setenv("RAGCRAFT_API_CONNECT_TIMEOUT_SECONDS", "7")
    monkeypatch.setenv("RAGCRAFT_API_READ_TIMEOUT_SECONDS", "120")
    cfg = fg_settings.load_frontend_backend_settings()
    assert cfg.api_connect_timeout_seconds == 7.0
    assert cfg.api_read_timeout_seconds == 120.0
    assert cfg.timeout_seconds == 120.0
    fg_settings.load_frontend_backend_settings.cache_clear()
