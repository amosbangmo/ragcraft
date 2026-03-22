"""
End-to-end HTTP pipeline validation (FastAPI TestClient only).

Exercises the main workspace → ingest → RAG → evaluation → export flow **through HTTP** with
dependency overrides so the full LangChain / unstructured graph is not required. No direct calls to
``src.infrastructure.adapters`` or use cases from test bodies—only ``TestClient`` requests and response assertions.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.dependencies import (
    get_ask_question_use_case,
    get_build_benchmark_export_artifacts_use_case,
    get_create_project_use_case,
    get_ingest_uploaded_file_use_case,
    get_inspect_pipeline_use_case,
    get_resolve_project_use_case,
    get_run_gold_qa_dataset_evaluation_use_case,
)
from apps.api.main import create_app
from apps.api.schemas.chat import ChatAskResponse, PipelineInspectResponse
from apps.api.schemas.evaluation import BenchmarkResultResponse
from apps.api.schemas.projects import CreateProjectResponse, IngestDocumentResponse
from src.application.use_cases.evaluation.build_benchmark_export_artifacts import (
    BuildBenchmarkExportArtifactsUseCase,
)
from src.application.ingestion.dtos import IngestDocumentResult
from src.domain.benchmark_result import BenchmarkResult, BenchmarkRow, BenchmarkSummary
from src.domain.ingestion_diagnostics import IngestionDiagnostics
from src.domain.pipeline_payloads import PipelineBuildResult
from src.domain.project import Project
from src.domain.rag_response import RAGResponse


def _hdr(uid: str = "e2e-http-user") -> dict[str, str]:
    return {"X-User-Id": uid}


class _CallableUseCase:
    def __init__(self, fn: Callable[..., Any]) -> None:
        self._fn = fn

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        return self._fn(*args, **kwargs)


class _FakeProjectWorkspace:
    def get_project(self, user_id: str, project_id: str) -> Project:
        return Project(user_id=user_id, project_id=project_id)


class _FakeResolveProjectUseCase:
    def __init__(self, inner: _FakeProjectWorkspace) -> None:
        self._inner = inner

    def execute(self, user_id: str, project_id: str) -> Project:
        return self._inner.get_project(user_id, project_id)


@pytest.fixture
def pipeline_client() -> Iterator[tuple[TestClient, FastAPI]]:
    """Single app with overrides for a full HTTP-only walk through core routes."""
    app = create_app()
    workspace = _FakeProjectWorkspace()

    app.dependency_overrides[get_create_project_use_case] = lambda: _CallableUseCase(
        lambda uid, pid: None
    )
    app.dependency_overrides[get_resolve_project_use_case] = lambda: _FakeResolveProjectUseCase(
        workspace
    )
    app.dependency_overrides[get_ingest_uploaded_file_use_case] = lambda: _CallableUseCase(
        lambda cmd: IngestDocumentResult(
            raw_assets=[{"id": "a1", "content_type": "text"}],
            replacement_info={"deleted_vectors": 0},
            diagnostics=IngestionDiagnostics(total_ms=5.0, generated_assets=1),
        )
    )
    app.dependency_overrides[get_ask_question_use_case] = lambda: _CallableUseCase(
        lambda project, question, *a, **k: RAGResponse(
            question=question,
            answer="HTTP-only answer.",
            confidence=0.88,
            latency={"total_ms": 42.0},
        )
    )
    app.dependency_overrides[get_inspect_pipeline_use_case] = lambda: _CallableUseCase(
        lambda *a, **k: PipelineBuildResult()
    )
    app.dependency_overrides[get_run_gold_qa_dataset_evaluation_use_case] = lambda: _CallableUseCase(
        lambda cmd: BenchmarkResult(
            summary=BenchmarkSummary(data={"rows": 1}),
            rows=[BenchmarkRow(entry_id=1, question="Q?", data={})],
            run_id="e2e-run",
        )
    )
    app.dependency_overrides[get_build_benchmark_export_artifacts_use_case] = (
        lambda: BuildBenchmarkExportArtifactsUseCase()
    )

    with TestClient(app) as tc:
        yield tc, app
    app.dependency_overrides.clear()


def test_http_pipeline_project_ingest_chat_inspect_benchmark_export(
    pipeline_client: tuple[TestClient, FastAPI],
) -> None:
    tc, _ = pipeline_client
    uid = "e2e-http-user"
    project_id = "e2e-project"
    h = _hdr(uid)

    r0 = tc.post("/projects", headers=h, json={"project_id": project_id})
    assert r0.status_code == 201
    created = CreateProjectResponse.model_validate(r0.json())
    assert created.project_id == project_id

    r1 = tc.post(
        f"/projects/{project_id}/documents/ingest",
        headers=h,
        files={"file": ("note.txt", b"hello e2e", "text/plain")},
    )
    assert r1.status_code == 200
    ing = IngestDocumentResponse.model_validate(r1.json())
    assert ing.diagnostics.total_ms == 5.0
    assert len(ing.raw_assets) == 1

    r2 = tc.post(
        "/chat/ask",
        headers=h,
        json={"project_id": project_id, "question": "What did we ingest?"},
    )
    assert r2.status_code == 200
    ask = ChatAskResponse.model_validate(r2.json())
    assert ask.status == "answered"
    assert ask.answer == "HTTP-only answer."
    assert ask.confidence == 0.88

    r3 = tc.post(
        "/chat/pipeline/inspect",
        headers=h,
        json={"project_id": project_id, "question": "Inspect pipeline"},
    )
    assert r3.status_code == 200
    insp = PipelineInspectResponse.model_validate(r3.json())
    assert insp.status in ("ok", "no_pipeline")

    r4 = tc.post(
        "/evaluation/dataset/run",
        headers=h,
        json={
            "project_id": project_id,
            "enable_query_rewrite": True,
            "enable_hybrid_retrieval": False,
        },
    )
    assert r4.status_code == 200
    bench = BenchmarkResultResponse.model_validate(r4.json())
    assert bench.run_id == "e2e-run"
    assert bench.summary.get("rows") == 1
    assert len(bench.rows) == 1

    r5 = tc.get("/evaluation/export/benchmark")
    assert r5.status_code == 200
    assert r5.json().get("implemented") is True

    r6 = tc.post(
        "/evaluation/export/benchmark",
        json={
            "project_id": project_id,
            "enable_query_rewrite": False,
            "enable_hybrid_retrieval": True,
            "result": {"summary": {"rows": 1}, "rows": bench.rows, "run_id": bench.run_id},
        },
    )
    assert r6.status_code == 200
    bundle = r6.json()
    raw = base64.standard_b64decode(bundle["json_base64"])
    exported = json.loads(raw.decode("utf-8"))
    assert exported["metadata"]["project_id"] == project_id


@pytest.mark.parametrize(
    "method,path,kwargs",
    [
        ("POST", "/projects", {"json": {"project_id": "x"}}),
        ("POST", "/projects/x/documents/ingest", {"files": {"file": ("a.txt", b"a", "text/plain")}}),
        ("POST", "/chat/ask", {"json": {"project_id": "x", "question": "q"}}),
        ("POST", "/chat/pipeline/inspect", {"json": {"project_id": "x", "question": "q"}}),
        (
            "POST",
            "/evaluation/dataset/run",
            {"json": {"project_id": "x", "enable_query_rewrite": True, "enable_hybrid_retrieval": True}},
        ),
    ],
)
def test_http_scoped_routes_require_x_user_id(
    pipeline_client: tuple[TestClient, FastAPI],
    method: str,
    path: str,
    kwargs: dict[str, Any],
) -> None:
    tc, _ = pipeline_client
    r = tc.request(method, path, **kwargs)
    assert r.status_code == 400
    err = r.json()
    assert err.get("code") == "http_400"
    assert "X-User-Id" in (err.get("message") or "")


def test_http_chat_ask_validation_error_returns_422(pipeline_client: tuple[TestClient, FastAPI]) -> None:
    tc, _ = pipeline_client
    r = tc.post(
        "/chat/ask",
        headers=_hdr(),
        json={"project_id": "p", "question": ""},
    )
    assert r.status_code == 422
    body = r.json()
    assert body.get("code") == "request_validation_failed"
