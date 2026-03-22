from __future__ import annotations

import base64
import json

import pytest
from fastapi.testclient import TestClient

from apps.api.dependencies import get_build_benchmark_export_artifacts_use_case
from apps.api.main import create_app
from src.application.evaluation.use_cases.build_benchmark_export_artifacts import (
    BuildBenchmarkExportArtifactsUseCase,
)


@pytest.fixture
def client() -> TestClient:
    """Inject the export use case only so tests do not require the full service graph (e.g. unstructured)."""
    app = create_app()
    app.dependency_overrides[get_build_benchmark_export_artifacts_use_case] = (
        lambda: BuildBenchmarkExportArtifactsUseCase()
    )
    with TestClient(app) as tc:
        yield tc
    app.dependency_overrides.clear()


def _export_body(**overrides: object) -> dict:
    body: dict = {
        "project_id": "demo",
        "enable_query_rewrite": False,
        "enable_hybrid_retrieval": True,
        "result": {"summary": {"rows": 0}, "rows": []},
    }
    body.update(overrides)
    return body


def test_get_benchmark_export_discovery(client: TestClient) -> None:
    r = client.get("/evaluation/export/benchmark")
    assert r.status_code == 200
    data = r.json()
    assert data.get("implemented") is True
    assert "all" in (data.get("formats") or [])


def test_post_benchmark_export_bundle_all_default_format(client: TestClient) -> None:
    r = client.post("/evaluation/export/benchmark", json=_export_body())
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/json")
    data = r.json()
    assert "metadata" in data
    assert data["metadata"]["project_id"] == "demo"
    for key in ("json_base64", "csv_base64", "markdown_base64", "json_filename", "csv_filename", "markdown_filename"):
        assert key in data
    raw_json = base64.standard_b64decode(data["json_base64"])
    parsed = json.loads(raw_json.decode("utf-8"))
    assert parsed["metadata"]["project_id"] == "demo"
    assert "summary" in parsed


def test_post_benchmark_export_file_json(client: TestClient) -> None:
    r = client.post("/evaluation/export/benchmark", json=_export_body(export_format="json"))
    assert r.status_code == 200
    ct = r.headers.get("content-type", "")
    assert "application/json" in ct
    cd = r.headers.get("content-disposition", "")
    assert "attachment" in cd.lower()
    assert ".json" in cd
    parsed = json.loads(r.content.decode("utf-8"))
    assert parsed["metadata"]["project_id"] == "demo"


def test_post_benchmark_export_file_csv(client: TestClient) -> None:
    r = client.post("/evaluation/export/benchmark", json=_export_body(export_format="csv"))
    assert r.status_code == 200
    ct = r.headers.get("content-type", "")
    assert "text/csv" in ct or "charset=utf-8" in ct
    cd = r.headers.get("content-disposition", "")
    assert "attachment" in cd.lower()
    assert ".csv" in cd
    text = r.content.decode("utf-8-sig")
    first = text.splitlines()[0]
    assert "entry_id" in first


def test_post_benchmark_export_file_markdown(client: TestClient) -> None:
    r = client.post("/evaluation/export/benchmark", json=_export_body(export_format="markdown"))
    assert r.status_code == 200
    ct = r.headers.get("content-type", "")
    assert "text/markdown" in ct
    cd = r.headers.get("content-disposition", "")
    assert "attachment" in cd.lower()
    assert ".md" in cd
    assert r.text.startswith("# RAGCraft benchmark")


def test_post_benchmark_export_invalid_format(client: TestClient) -> None:
    r = client.post("/evaluation/export/benchmark", json=_export_body(export_format="pdf"))
    assert r.status_code == 422


def test_post_benchmark_export_invalid_benchmark_payload(client: TestClient) -> None:
    r = client.post(
        "/evaluation/export/benchmark",
        json=_export_body(
            result={"summary": {}, "rows": [{"entry_id": "not-an-int", "question": "q"}]},
        ),
    )
    assert r.status_code == 422
    payload = r.json()
    ctx = payload.get("context")
    assert isinstance(ctx, dict)
    assert ctx.get("error") == "invalid_benchmark_payload"
