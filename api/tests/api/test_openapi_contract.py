"""Contract checks on OpenAPI and representative HTTP error envelopes (no heavy backend calls)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from interfaces.http.main import create_app


@pytest.fixture
def api_client() -> TestClient:
    return TestClient(create_app())


def _resolved_schema(spec: dict, schema_obj: dict) -> dict:
    ref = schema_obj.get("$ref")
    if ref and isinstance(ref, str) and ref.startswith("#/components/schemas/"):
        name = ref.rsplit("/", 1)[-1]
        return dict(spec["components"]["schemas"][name])
    return schema_obj


def test_openapi_includes_bearer_scheme_and_canonical_error_model(api_client: TestClient) -> None:
    r = api_client.get("/openapi.json")
    assert r.status_code == 200
    spec = r.json()
    schemes = spec["components"]["securitySchemes"]
    bearer = schemes["BearerAuth"]
    assert bearer["type"] == "http"
    assert bearer["scheme"] == "bearer"
    if "HTTPBearer" in schemes:
        assert schemes["HTTPBearer"]["type"] == "http"
        assert schemes["HTTPBearer"]["scheme"] == "bearer"
    canon = spec["components"]["schemas"]["CanonicalApiError"]
    assert "required" in canon
    assert set(canon["required"]) >= {"detail", "message", "error_type", "code", "category"}


def test_chat_ask_request_schema_has_no_body_user_id(api_client: TestClient) -> None:
    spec = api_client.get("/openapi.json").json()
    ask = spec["paths"]["/chat/ask"]["post"]
    body = ask["requestBody"]["content"]["application/json"]["schema"]
    schema = _resolved_schema(spec, body)
    assert "user_id" not in schema.get("properties", {})


def test_retrieval_compare_request_schema_has_no_body_user_id(api_client: TestClient) -> None:
    spec = api_client.get("/openapi.json").json()
    op = spec["paths"]["/chat/retrieval/compare"]["post"]
    body = op["requestBody"]["content"]["application/json"]["schema"]
    schema = _resolved_schema(spec, body)
    assert "user_id" not in schema.get("properties", {})


def test_openapi_tags_cover_surface_areas(api_client: TestClient) -> None:
    spec = api_client.get("/openapi.json").json()
    names: set[str] = set()
    for path_item in spec.get("paths", {}).values():
        for method, op in path_item.items():
            if method in frozenset(
                {"get", "post", "put", "patch", "delete", "head", "options"}
            ) and isinstance(op, dict):
                names.update(op.get("tags") or [])
    assert names >= {"chat", "projects", "evaluation", "users", "auth", "system"}


def test_missing_bearer_returns_canonical_error(api_client: TestClient) -> None:
    resp = api_client.post("/projects", json={"project_id": "demo"})
    assert resp.status_code == 401
    data = resp.json()
    assert data["code"] == "authentication_required"
    assert data["category"] == "application"
    assert data["message"] == data["detail"]


def test_openapi_documents_422_for_chat_ask(api_client: TestClient) -> None:
    """Body validation is documented without invoking chat dependencies (heavy composition)."""
    spec = api_client.get("/openapi.json").json()
    responses = spec["paths"]["/chat/ask"]["post"]["responses"]
    assert "422" in responses
    desc = responses["422"].get("description", "")
    assert "validation" in desc.lower()


def test_health_and_version_public(api_client: TestClient) -> None:
    assert api_client.get("/health").json() == {"status": "ok"}
    v = api_client.get("/version").json()
    assert "service" in v and "version" in v
